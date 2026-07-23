package com.footscan.app.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// ---------- auth ----------

@Serializable
data class LoginRequest(
    val email: String,
    val password: String,
)

@Serializable
data class LoginResponse(
    @SerialName("access_token") val accessToken: String,
    @SerialName("token_type") val tokenType: String = "bearer",
    val user: UserDto,
)

@Serializable
data class UserDto(
    val uuid: String,
    val name: String,
    val email: String,
    val role: String,
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("created_at") val createdAt: String? = null,
)

// ---------- patients ----------

@Serializable
data class PatientIn(
    val name: String,
    @SerialName("birth_date") val birthDate: String? = null,
    val sex: String? = null,
    val document: String? = null,
    val phone: String? = null,
    val email: String? = null,
    val notes: String? = null,
)

@Serializable
data class PatientDto(
    val uuid: String,
    val name: String,
    @SerialName("birth_date") val birthDate: String? = null,
    val sex: String? = null,
    val document: String? = null,
    val phone: String? = null,
    val email: String? = null,
    val notes: String? = null,
    @SerialName("consent_accepted_at") val consentAcceptedAt: String? = null,
    @SerialName("consent_version") val consentVersion: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
)

@Serializable
data class ConsentRequest(
    val version: String = "v1",
)

// ---------- measures ----------

@Serializable
data class QualityDto(
    @SerialName("markers_found") val markersFound: Int = 0,
    val warnings: List<String> = emptyList(),
)

@Serializable
data class MeasuresDto(
    val version: Int = 1,
    @SerialName("foot_side") val footSide: String? = null,
    @SerialName("scale_px_per_mm") val scalePxPerMm: Double? = null,
    @SerialName("length_mm") val lengthMm: Double? = null,
    @SerialName("forefoot_width_mm") val forefootWidthMm: Double? = null,
    @SerialName("midfoot_width_mm") val midfootWidthMm: Double? = null,
    @SerialName("heel_width_mm") val heelWidthMm: Double? = null,
    @SerialName("plantar_area_cm2") val plantarAreaCm2: Double? = null,
    @SerialName("axis_angle_deg") val axisAngleDeg: Double? = null,
    val landmarks: Map<String, List<Double>> = emptyMap(),
    @SerialName("contour_mm") val contourMm: List<List<Double>> = emptyList(),
    val quality: QualityDto? = null,
    @SerialName("manually_adjusted") val manuallyAdjusted: Boolean = false,
)

// ---------- exams / captures ----------

@Serializable
data class ExamCreateRequest(
    @SerialName("patient_uuid") val patientUuid: String,
    val notes: String? = null,
)

@Serializable
data class CaptureDto(
    val uuid: String,
    @SerialName("foot_side") val footSide: String,
    val view: String = "plantar",
    val processed: Boolean = false,
    val error: String? = null,
    val measures: MeasuresDto? = null,
    @SerialName("manually_adjusted") val manuallyAdjusted: Boolean = false,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class ExamDto(
    val uuid: String,
    @SerialName("patient_uuid") val patientUuid: String,
    val professional: UserDto? = null,
    val status: String = "draft",
    val notes: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    val captures: List<CaptureDto> = emptyList(),
)

@Serializable
data class AsymmetryDto(
    @SerialName("length_mm") val lengthMm: Double? = null,
    @SerialName("forefoot_width_mm") val forefootWidthMm: Double? = null,
    @SerialName("midfoot_width_mm") val midfootWidthMm: Double? = null,
    @SerialName("heel_width_mm") val heelWidthMm: Double? = null,
    @SerialName("plantar_area_cm2") val plantarAreaCm2: Double? = null,
)

@Serializable
data class PreviousExamDto(
    val uuid: String,
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("measures_by_side") val measuresBySide: Map<String, MeasuresDto?> = emptyMap(),
)

@Serializable
data class ExamDetailDto(
    val uuid: String,
    @SerialName("patient_uuid") val patientUuid: String,
    val professional: UserDto? = null,
    val status: String = "draft",
    val notes: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
    val captures: List<CaptureDto> = emptyList(),
    val asymmetry: AsymmetryDto? = null,
    @SerialName("previous_exam") val previousExam: PreviousExamDto? = null,
)

// ---------- history ----------

@Serializable
data class HistoryItemDto(
    @SerialName("exam_uuid") val examUuid: String,
    @SerialName("created_at") val createdAt: String? = null,
    val status: String = "draft",
    @SerialName("measures_by_side") val measuresBySide: Map<String, MeasuresDto?> = emptyMap(),
)

// ---------- sync ----------

@Serializable
data class SyncPatientDto(
    val uuid: String,
    val name: String,
    @SerialName("birth_date") val birthDate: String? = null,
    val sex: String? = null,
    val document: String? = null,
    val phone: String? = null,
    val email: String? = null,
    val notes: String? = null,
    @SerialName("consent_accepted_at") val consentAcceptedAt: String? = null,
    @SerialName("consent_version") val consentVersion: String? = null,
)

@Serializable
data class SyncExamDto(
    val uuid: String,
    @SerialName("patient_uuid") val patientUuid: String,
    val notes: String? = null,
    @SerialName("created_at") val createdAt: String? = null,
)

@Serializable
data class SyncBatchRequest(
    val patients: List<SyncPatientDto> = emptyList(),
    val exams: List<SyncExamDto> = emptyList(),
)

@Serializable
data class SyncCountsDto(
    val created: Int = 0,
    val updated: Int = 0,
)

@Serializable
data class SyncBatchResponse(
    val patients: SyncCountsDto = SyncCountsDto(),
    val exams: SyncCountsDto = SyncCountsDto(),
)
