package com.footscan.app.data.local

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "captures",
    indices = [Index("examUuid")],
)
data class CaptureEntity(
    @PrimaryKey val uuid: String,
    val examUuid: String,
    val footSide: String,
    val view: String = "plantar",
    val localImagePath: String,
    val processed: Boolean = false,
    val measuresJson: String? = null,
    val error: String? = null,
    val createdAt: String,
    val syncState: String = SyncState.PENDING,
)
