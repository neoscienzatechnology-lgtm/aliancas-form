package com.footscan.app.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "exams",
    indices = [Index("patientUuid")],
)
data class ExamEntity(
    @PrimaryKey val uuid: String,
    val patientUuid: String,
    val notes: String? = null,
    val status: String = "draft",
    val createdAt: String,
    val syncState: String = SyncState.PENDING,
)
