package com.footscan.app.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ExitToApp
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
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
import com.footscan.app.data.local.PatientEntity
import com.footscan.app.data.local.SyncState
import com.footscan.app.di.AppContainer
import com.footscan.app.ui.Routes
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PatientListScreen(container: AppContainer, navController: NavHostController) {
    var search by remember { mutableStateOf("") }
    val patients by container.patientRepository
        .observePatients(search)
        .collectAsState(initial = emptyList())
    val scope = rememberCoroutineScope()

    LaunchedEffect(Unit) {
        // Atualiza o cache local silenciosamente quando há rede.
        runCatching { container.patientRepository.refreshFromServer() }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Pacientes") },
                actions = {
                    IconButton(onClick = { navController.navigate(Routes.SETTINGS) }) {
                        Icon(Icons.Filled.Settings, contentDescription = "Configurações")
                    }
                    IconButton(onClick = {
                        scope.launch {
                            container.authRepository.logout()
                            navController.navigate(Routes.LOGIN) {
                                popUpTo(0) { inclusive = true }
                            }
                        }
                    }) {
                        Icon(Icons.AutoMirrored.Filled.ExitToApp, contentDescription = "Sair")
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { navController.navigate(Routes.patientForm()) }) {
                Icon(Icons.Filled.Add, contentDescription = "Novo paciente")
            }
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
        ) {
            OutlinedTextField(
                value = search,
                onValueChange = { search = it },
                label = { Text("Buscar por nome ou documento") },
                leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                singleLine = true,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp),
            )

            if (patients.isEmpty()) {
                Text(
                    text = "Nenhum paciente encontrado. Toque em + para cadastrar.",
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(vertical = 24.dp),
                )
            }

            LazyColumn {
                items(patients, key = { it.uuid }) { patient ->
                    PatientRow(
                        patient = patient,
                        onClick = { navController.navigate(Routes.examNew(patient.uuid)) },
                        onEdit = { navController.navigate(Routes.patientForm(patient.uuid)) },
                    )
                }
            }
        }
    }
}

@Composable
private fun PatientRow(
    patient: PatientEntity,
    onClick: () -> Unit,
    onEdit: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .clickable(onClick = onClick),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(text = patient.name, style = MaterialTheme.typography.titleMedium)
            val subtitle = buildString {
                patient.document?.let { append("Documento: $it") }
                if (patient.consentAcceptedAt == null) {
                    if (isNotEmpty()) append(" — ")
                    append("Sem consentimento")
                }
                if (patient.syncState == SyncState.PENDING) {
                    if (isNotEmpty()) append(" — ")
                    append("Aguardando sincronização")
                }
            }
            if (subtitle.isNotEmpty()) {
                Text(text = subtitle, style = MaterialTheme.typography.bodySmall)
            }
            Text(
                text = "Editar cadastro",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier
                    .padding(top = 4.dp)
                    .clickable(onClick = onEdit),
            )
        }
    }
}
