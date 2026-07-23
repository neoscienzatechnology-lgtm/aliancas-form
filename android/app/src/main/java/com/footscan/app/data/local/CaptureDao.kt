package com.footscan.app.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface CaptureDao {

    @Query("SELECT * FROM captures WHERE examUuid = :examUuid ORDER BY createdAt")
    fun observeByExam(examUuid: String): Flow<List<CaptureEntity>>

    @Query("SELECT * FROM captures WHERE uuid = :uuid")
    suspend fun getByUuid(uuid: String): CaptureEntity?

    @Query(
        "SELECT * FROM captures WHERE examUuid = :examUuid AND footSide = :footSide AND view = :view LIMIT 1"
    )
    suspend fun getByExamSideView(examUuid: String, footSide: String, view: String): CaptureEntity?

    @Query("SELECT * FROM captures WHERE syncState = 'PENDING' ORDER BY createdAt")
    suspend fun pendingUploads(): List<CaptureEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(capture: CaptureEntity)

    @Query("DELETE FROM captures WHERE uuid = :uuid")
    suspend fun delete(uuid: String)
}
