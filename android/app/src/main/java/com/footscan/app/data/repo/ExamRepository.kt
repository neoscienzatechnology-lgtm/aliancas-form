package com.footscan.app.data.repo

import android.content.Context
import com.footscan.app.data.api.ApiService
import com.footscan.app.data.api.ExamDetailDto
import com.footscan.app.data.api.HistoryItemDto
import com.footscan.app.data.local.CaptureDao
import com.footscan.app.data.local.CaptureEntity
import com.footscan.app.data.local.ExamDao
import com.footscan.app.data.local.ExamEntity
import com.footscan.app.data.local.SyncState
import com.footscan.app.sync.SyncWorker
import kotlinx.coroutines.flow.Flow
import java.io.File
import java.time.Instant

/**
 * Offline-first: exames e capturas são gravados no Room e sincronizados em
 * segundo plano (sync/batch para exames; upload multipart com client_uuid
 * para as imagens).
 */
class ExamRepository(
    private val examDao: ExamDao,
    private val captureDao: CaptureDao,
    private val apiProvider: suspend () -> ApiService,
    private val appContext: Context,
) {

    fun observeExams(patientUuid: String): Flow<List<ExamEntity>> =
        examDao.observeByPatient(patientUuid)

    fun observeCaptures(examUuid: String): Flow<List<CaptureEntity>> =
        captureDao.observeByExam(examUuid)

    suspend fun getExam(uuid: String): ExamEntity? = examDao.getByUuid(uuid)

    suspend fun createExam(patientUuid: String, notes: String?): ExamEntity {
        val exam = ExamEntity(
            uuid = PatientRepository.newUuid(),
            patientUuid = patientUuid,
            notes = notes?.ifBlank { null },
            status = "draft",
            createdAt = Instant.now().toString(),
            syncState = SyncState.PENDING,
        )
        examDao.upsert(exam)
        SyncWorker.enqueue(appContext)
        return exam
    }

    /**
     * Registra a foto capturada localmente e enfileira o upload.
     * Substitui a captura local existente do mesmo (exame, pé, vista),
     * espelhando a regra do servidor.
     */
    suspend fun saveCapture(
        examUuid: String,
        footSide: String,
        imageFile: File,
        view: String = "plantar",
    ): CaptureEntity {
        val existing = captureDao.getByExamSideView(examUuid, footSide, view)
        if (existing != null && existing.localImagePath != imageFile.absolutePath) {
            runCatching { File(existing.localImagePath).delete() }
        }
        val capture = CaptureEntity(
            uuid = existing?.uuid ?: PatientRepository.newUuid(),
            examUuid = examUuid,
            footSide = footSide,
            view = view,
            localImagePath = imageFile.absolutePath,
            processed = false,
            measuresJson = null,
            error = null,
            createdAt = Instant.now().toString(),
            syncState = SyncState.PENDING,
        )
        captureDao.upsert(capture)
        SyncWorker.enqueue(appContext)
        return capture
    }

    /** Detalhe do exame com medidas/assimetria — exige conexão com o servidor. */
    suspend fun fetchExamDetail(examUuid: String): ExamDetailDto =
        apiProvider().getExam(examUuid)

    /** Histórico do paciente (base da comparação entre exames) — exige conexão. */
    suspend fun fetchHistory(patientUuid: String): List<HistoryItemDto> =
        apiProvider().patientHistory(patientUuid)

    /** Diretório local das imagens capturadas. */
    fun capturesDir(): File =
        File(appContext.filesDir, "captures").apply { mkdirs() }
}
