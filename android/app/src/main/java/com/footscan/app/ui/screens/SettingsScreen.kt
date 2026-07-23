package com.footscan.app.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.footscan.app.data.settings.SettingsStore
import com.footscan.app.di.AppContainer
import com.footscan.app.sync.SyncWorker
import androidx.compose.ui.platform.LocalContext
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(container: AppContainer, navController: NavHostController) {
    val context = LocalContext.current
    var serverUrl by remember { mutableStateOf("") }
    var saved by remember { mutableStateOf(false) }
    val userName by container.settings.userName.collectAsState(initial = null)
    val userEmail by container.settings.userEmail.collectAsState(initial = null)
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        serverUrl = container.settings.serverUrl.first()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Configurações") },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Voltar")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
        ) {
            Text(text = "Servidor", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = serverUrl,
                onValueChange = {
                    serverUrl = it
                    saved = false
                },
                label = { Text("URL do servidor FootScan") },
                placeholder = { Text(SettingsStore.DEFAULT_SERVER_URL) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Text(
                text = "Ex.: ${SettingsStore.DEFAULT_SERVER_URL} (emulador Android → " +
                    "servidor local na porta 8000).",
                style = MaterialTheme.typography.labelSmall,
            )
            Spacer(modifier = Modifier.height(12.dp))
            Button(
                onClick = {
                    scope.launch {
                        container.settings.setServerUrl(serverUrl.trim().trimEnd('/'))
                        saved = true
                    }
                },
                enabled = serverUrl.isNotBlank(),
            ) {
                Text("Salvar")
            }
            if (saved) {
                Text(
                    text = "URL salva.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.primary,
                )
            }

            Spacer(modifier = Modifier.height(24.dp))
            Text(text = "Sincronização", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Button(onClick = { SyncWorker.enqueue(context) }) {
                Text("Sincronizar agora")
            }
            Text(
                text = "Pacientes, exames e imagens pendentes são enviados " +
                    "automaticamente quando há rede.",
                style = MaterialTheme.typography.labelSmall,
            )

            if (userName != null) {
                Spacer(modifier = Modifier.height(24.dp))
                Text(text = "Sessão", style = MaterialTheme.typography.titleMedium)
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Conectado como $userName (${userEmail ?: "—"})",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}
