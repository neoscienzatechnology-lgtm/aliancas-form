package com.footscan.app.data.repo

import com.footscan.app.data.api.ApiService
import com.footscan.app.data.api.LoginRequest
import com.footscan.app.data.api.UserDto
import com.footscan.app.data.settings.SettingsStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

class AuthRepository(
    private val settings: SettingsStore,
    private val apiProvider: suspend () -> ApiService,
) {

    val isLoggedIn: Flow<Boolean> = settings.authToken.map { !it.isNullOrBlank() }

    val userName: Flow<String?> = settings.userName

    /**
     * Autentica no servidor e persiste token + dados do usuário.
     * Login exige conexão; o restante do app funciona offline.
     */
    suspend fun login(email: String, password: String): Result<UserDto> {
        return try {
            val response = apiProvider().login(LoginRequest(email = email, password = password))
            settings.setSession(
                token = response.accessToken,
                userName = response.user.name,
                userEmail = response.user.email,
            )
            Result.success(response.user)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun logout() {
        settings.clearSession()
    }
}
