package com.footscan.app.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface PatientDao {

    @Query(
        """
        SELECT * FROM patients
        WHERE name LIKE '%' || :search || '%' OR document LIKE '%' || :search || '%'
        ORDER BY name COLLATE NOCASE
        """
    )
    fun observePatients(search: String): Flow<List<PatientEntity>>

    @Query("SELECT * FROM patients WHERE uuid = :uuid")
    suspend fun getByUuid(uuid: String): PatientEntity?

    @Query("SELECT * FROM patients WHERE uuid = :uuid")
    fun observeByUuid(uuid: String): Flow<PatientEntity?>

    @Query("SELECT * FROM patients WHERE syncState = 'PENDING'")
    suspend fun pending(): List<PatientEntity>

    @Query("UPDATE patients SET syncState = 'SYNCED' WHERE uuid IN (:uuids)")
    suspend fun markSynced(uuids: List<String>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(patient: PatientEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(patients: List<PatientEntity>)
}
