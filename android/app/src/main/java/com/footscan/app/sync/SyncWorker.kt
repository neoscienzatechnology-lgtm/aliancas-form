package com.footscan.app.sync

import android.content.Context
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import com.footscan.app.FootScanApp
import com.footscan.app.data.api.ApiClient
import com.footscan.app.data.api.MeasuresDto
import com.footscan.app.data.api.SyncBatchRequest
import com.footscan.app.data.api.SyncExamDto
import com.footscan.app.data.api.SyncPatientDto
import com.footscan.app.data.local.SyncState
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException
import java.io.File
import java.io.IOException

/**
 * Sincronização offline-first:
 * 1. POST /api/sync/batch com pacientes e exames pendentes (upsert por uuid);
 * 2. upload das imagens pendentes via POST /api/exams/{uuid}/captures com
 *    client_uuid (idempotente — re-execuções não duplicam capturas).
 *
 * Executa somente com rede disponível (constraint NetworkType.CONNECTED).
 */
class SyncWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {

    override suspend fun doWork(): Result {
        val app = applicationContext as FootScanApp
        val container = app.container
        val patientDao = container.database.patientDao()
        val examDao = container.database.examDao()
        val captureDao = container.database.captureDao()

        return try {
            val api = container.api()

            // 1) Pacientes e exames pendentes em um único batch (ordem: patients -> exams).
            val pendingPatients = patientDao.pending()
            val pendingExams = examDao.pending()
            if (pendingPatients.isNotEmpty() || pendingExams.isNotEmpty()) {
                val request = SyncBatchRequest(
                    patients = pendingPatients.map { p ->
                        SyncPatientDto(
                            uuid = p.uuid,
                            name = p.name,
                            birthDate = p.birthDate,
                            sex = p.sex,
                            document = p.document,
                            phone = p.phone,
                            email = p.email,
                            notes = p.notes,
                            consentAcceptedAt = p.consentAcceptedAt,
                            consentVersion = p.consentVersion,
                        )
                    },
                    exams = pendingExams.map { e ->
                        SyncExamDto(
                            uuid = e.uuid,
                            patientUuid = e.patientUuid,
                            notes = e.notes,
                            createdAt = e.createdAt,
                        )
                    },
                )
                api.syncBatch(request)
                if (pendingPatients.isNotEmpty()) {
                    patientDao.markSynced(pendingPatients.map { it.uuid })
                }
                if (pendingExams.isNotEmpty()) {
                    examDao.markSynced(pendingExams.map { it.uuid })
                }
            }

            // 2) Upload das imagens pendentes (client_uuid garante idempotência).
            for (capture in captureDao.pendingUploads()) {
                val file = File(capture.localImagePath)
                if (!file.exists()) {
                    captureDao.upsert(
                        capture.copy(
                            error = "Arquivo de imagem não encontrado no dispositivo",
                            syncState = SyncState.SYNCED,
                        )
                    )
                    continue
                }
                val filePart = MultipartBody.Part.createFormData(
                    "file",
                    file.name,
                    file.asRequestBody("image/jpeg".toMediaType()),
                )
                val response = api.uploadCapture(
                    examUuid = capture.examUuid,
                    footSide = capture.footSide.toPlainBody(),
                    view = capture.view.toPlainBody(),
                    clientUuid = capture.uuid.toPlainBody(),
                    file = filePart,
                )
                if (response.uuid != capture.uuid) {
                    captureDao.delete(capture.uuid)
                }
                captureDao.upsert(
                    capture.copy(
                        uuid = response.uuid,
                        processed = response.processed,
                        measuresJson = response.measures?.let {
                            ApiClient.json.encodeToString(MeasuresDto.serializer(), it)
                        },
                        error = response.error,
                        syncState = SyncState.SYNCED,
                    )
                )
                if (response.processed) {
                    examDao.updateStatus(capture.examUuid, "processed")
                }
            }

            Result.success()
        } catch (e: IOException) {
            // Sem rede / servidor indisponível: tenta de novo mais tarde.
            Result.retry()
        } catch (e: HttpException) {
            if (e.code() in 500..599) Result.retry() else Result.failure()
        } catch (e: Exception) {
            Result.failure()
        }
    }

    private fun String.toPlainBody(): RequestBody =
        toRequestBody("text/plain".toMediaType())

    companion object {
        private const val UNIQUE_WORK_NAME = "footscan_sync"

        fun enqueue(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val request = OneTimeWorkRequestBuilder<SyncWorker>()
                .setConstraints(constraints)
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(
                UNIQUE_WORK_NAME,
                ExistingWorkPolicy.APPEND_OR_REPLACE,
                request,
            )
        }
    }
}
