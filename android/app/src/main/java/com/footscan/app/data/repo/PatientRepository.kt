package com.footscan.app.data.repo

import android.content.Context
import com.footscan.app.data.api.ApiService
import com.footscan.app.data.api.PatientDto
import com.footscan.app.data.local.PatientDao
import com.footscan.app.data.local.PatientEntity
import com.footscan.app.data.local.SyncState
import com.footscan.app.sync.SyncWorker
import kotlinx.coroutines.flow.Flow
import java.time.Instant
import java.util.UUID

/**
 * Offline-first: toda escrita vai para o Room com syncState=PENDING e a
 * sincronização é enfileirada no WorkManager (SyncWorker → POST /api/sync/batch).
 */
class PatientRepository(
    private val patientDao: PatientDao,
    private val apiProvider: suspend () -> ApiService,
    private val appContext: Context,
) {

    fun observePatients(search: String): Flow<List<PatientEntity>> =
        patientDao.observePatients(search)

    fun observePatient(uuid: String): Flow<PatientEntity?> = patientDao.observeByUuid(uuid)

    suspend fun getPatient(uuid: String): PatientEntity? = patientDao.getByUuid(uuid)

    suspend fun savePatient(
        uuid: String?,
        name: String,
        birthDate: String?,
        sex: String?,
        document: String?,
        phone: String?,
        email: String?,
        notes: String?,
        consentAccepted: Boolean,
        consentVersion: String = "v1",
    ): PatientEntity {
        val now = Instant.now().toString()
        val existing = uuid?.let { patientDao.getByUuid(it) }
        val entity = PatientEntity(
            uuid = existing?.uuid ?: newUuid(),
            name = name,
            birthDate = birthDate?.ifBlank { null },
            sex = sex?.ifBlank { null },
            document = document?.ifBlank { null },
            phone = phone?.ifBlank { null },
            email = email?.ifBlank { null },
            notes = notes?.ifBlank { null },
            consentAcceptedAt = when {
                consentAccepted && existing?.consentAcceptedAt != null -> existing.consentAcceptedAt
                consentAccepted -> now
                else -> null
            },
            consentVersion = if (consentAccepted) consentVersion else null,
            createdAt = existing?.createdAt ?: now,
            updatedAt = now,
            syncState = SyncState.PENDING,
        )
        patientDao.upsert(entity)
        SyncWorker.enqueue(appContext)
        return entity
    }

    suspend fun registerConsent(uuid: String, version: String = "v1"): PatientEntity? {
        val existing = patientDao.getByUuid(uuid) ?: return null
        val now = Instant.now().toString()
        val updated = existing.copy(
            consentAcceptedAt = existing.consentAcceptedAt ?: now,
            consentVersion = version,
            updatedAt = now,
            syncState = SyncState.PENDING,
        )
        patientDao.upsert(updated)
        SyncWorker.enqueue(appContext)
        return updated
    }

    /**
     * Puxa pacientes do servidor para o cache local. Registros locais com
     * alteração pendente nunca são sobrescritos.
     */
    suspend fun refreshFromServer(search: String? = null) {
        val remote: List<PatientDto> = apiProvider().listPatients(search)
        for (dto in remote) {
            val local = patientDao.getByUuid(dto.uuid)
            if (local != null && local.syncState == SyncState.PENDING) continue
            patientDao.upsert(
                PatientEntity(
                    uuid = dto.uuid,
                    name = dto.name,
                    birthDate = dto.birthDate,
                    sex = dto.sex,
                    document = dto.document,
                    phone = dto.phone,
                    email = dto.email,
                    notes = dto.notes,
                    consentAcceptedAt = dto.consentAcceptedAt,
                    consentVersion = dto.consentVersion,
                    createdAt = dto.createdAt ?: Instant.now().toString(),
                    updatedAt = dto.updatedAt ?: Instant.now().toString(),
                    syncState = SyncState.SYNCED,
                )
            )
        }
    }

    companion object {
        fun newUuid(): String = UUID.randomUUID().toString().replace("-", "")
    }
}
