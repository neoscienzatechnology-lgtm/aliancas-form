package com.footscan.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "patients")
data class PatientEntity(
    @PrimaryKey val uuid: String,
    val name: String,
    val birthDate: String? = null,
    val sex: String? = null,
    val document: String? = null,
    val phone: String? = null,
    val email: String? = null,
    val notes: String? = null,
    val consentAcceptedAt: String? = null,
    val consentVersion: String? = null,
    val createdAt: String,
    val updatedAt: String,
    val syncState: String = SyncState.PENDING,
)
