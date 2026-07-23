package com.footscan.app.di

import android.content.Context
import com.footscan.app.data.api.ApiClient
import com.footscan.app.data.api.ApiService
import com.footscan.app.data.local.AppDatabase
import com.footscan.app.data.repo.AuthRepository
import com.footscan.app.data.repo.ExamRepository
import com.footscan.app.data.repo.PatientRepository
import com.footscan.app.data.settings.SettingsStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.runBlocking

/**
 * Container simples de dependências (sem framework de DI no scaffold).
 */
class AppContainer(private val appContext: Context) {

    val settings: SettingsStore = SettingsStore(appContext)

    val database: AppDatabase by lazy { AppDatabase.build(appContext) }

    @Volatile
    private var cachedApi: Pair<String, ApiService>? = null

    /**
     * Retorna um ApiService apontando para a URL configurada em Settings.
     * Recria o Retrofit quando a URL do servidor muda.
     */
    suspend fun api(): ApiService {
        val baseUrl = settings.serverUrl.first().trimEnd('/') + "/"
        cachedApi?.let { (url, service) -> if (url == baseUrl) return service }
        val service = ApiClient.create(baseUrl) {
            runBlocking { settings.authToken.firstOrNull() }
        }
        cachedApi = baseUrl to service
        return service
    }

    val authRepository: AuthRepository by lazy {
        AuthRepository(settings = settings, apiProvider = ::api)
    }

    val patientRepository: PatientRepository by lazy {
        PatientRepository(
            patientDao = database.patientDao(),
            apiProvider = ::api,
            appContext = appContext,
        )
    }

    val examRepository: ExamRepository by lazy {
        ExamRepository(
            examDao = database.examDao(),
            captureDao = database.captureDao(),
            apiProvider = ::api,
            appContext = appContext,
        )
    }
}
