package com.footscan.app.data.api

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Espelho da API REST do servidor FootScan (ver SPEC.md).
 * Todas as rotas exceto login exigem header Authorization: Bearer <token>
 * (adicionado pelo interceptor em ApiClient).
 */
interface ApiService {

    // ---------- auth ----------

    @POST("api/auth/login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @GET("api/auth/me")
    suspend fun me(): UserDto

    // ---------- patients ----------

    @GET("api/patients")
    suspend fun listPatients(@Query("search") search: String? = null): List<PatientDto>

    @POST("api/patients")
    suspend fun createPatient(@Body body: PatientIn): PatientDto

    @GET("api/patients/{uuid}")
    suspend fun getPatient(@Path("uuid") uuid: String): PatientDto

    @PUT("api/patients/{uuid}")
    suspend fun updatePatient(@Path("uuid") uuid: String, @Body body: PatientIn): PatientDto

    @POST("api/patients/{uuid}/consent")
    suspend fun registerConsent(@Path("uuid") uuid: String, @Body body: ConsentRequest): PatientDto

    @GET("api/patients/{uuid}/history")
    suspend fun patientHistory(@Path("uuid") uuid: String): List<HistoryItemDto>

    // ---------- exams ----------

    @POST("api/exams")
    suspend fun createExam(@Body body: ExamCreateRequest): ExamDto

    @GET("api/exams")
    suspend fun listExams(@Query("patient_uuid") patientUuid: String? = null): List<ExamDto>

    @GET("api/exams/{uuid}")
    suspend fun getExam(@Path("uuid") uuid: String): ExamDetailDto

    // ---------- captures ----------

    @Multipart
    @POST("api/exams/{uuid}/captures")
    suspend fun uploadCapture(
        @Path("uuid") examUuid: String,
        @Part("foot_side") footSide: RequestBody,
        @Part("view") view: RequestBody,
        @Part("client_uuid") clientUuid: RequestBody,
        @Part file: MultipartBody.Part,
    ): CaptureDto

    // ---------- sync ----------

    @POST("api/sync/batch")
    suspend fun syncBatch(@Body body: SyncBatchRequest): SyncBatchResponse
}
