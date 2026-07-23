package com.footscan.app.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface ExamDao {

    @Query("SELECT * FROM exams WHERE patientUuid = :patientUuid ORDER BY createdAt DESC")
    fun observeByPatient(patientUuid: String): Flow<List<ExamEntity>>

    @Query("SELECT * FROM exams WHERE uuid = :uuid")
    suspend fun getByUuid(uuid: String): ExamEntity?

    @Query("SELECT * FROM exams WHERE syncState = 'PENDING'")
    suspend fun pending(): List<ExamEntity>

    @Query("UPDATE exams SET syncState = 'SYNCED' WHERE uuid IN (:uuids)")
    suspend fun markSynced(uuids: List<String>)

    @Query("UPDATE exams SET status = :status WHERE uuid = :uuid")
    suspend fun updateStatus(uuid: String, status: String)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(exam: ExamEntity)
}
