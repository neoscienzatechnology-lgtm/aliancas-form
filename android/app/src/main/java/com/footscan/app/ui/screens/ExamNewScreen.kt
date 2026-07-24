package com.footscan.app.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.footscan.app.data.local.ExamEntity
import com.footscan.app.di.AppContainer
import com.footscan.app.ui.Routes
import kotlinx.coroutines.launch

/**
 * Seleção do exame: inicia um novo exame para o paciente ou abre um exame
 * existente (resultados). Exige consentimento LGPD registrado.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ExamNewScreen(
    container: AppContainer,
    navController: NavHostController,
    patientUuid: String,
) {
    val patient by container.patientRepository
        .observePatient(patientUuid)
        .collectAsState(initial = null)
    val exams by container.examRepository
        .observeExams(patientUuid)
        .collectAsState(initial = emptyList())
    var notes by remember { mutableStateOf("") }
    var creating by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    val hasConsent = patient?.consentAcceptedAt != null

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(patient?.name ?: "Exame") },
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
            Text(text = "Novo exame", style = MaterialTheme.typography.titleLarge)
            Spacer(modifier = Modifier.height(8.dp))

            if (!hasConsent) {
                Text(
                    text = "Este paciente ainda não possui consentimento LGPD registrado. " +
                        "Edite o cadastro e registre o consentimento antes de criar um exame.",
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium,
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedButton(onClick = { navController.navigate(Routes.patientForm(patientUuid)) }) {
                    Text("Abrir cadastro do paciente")
                }
                Spacer(modifier = Modifier.height(16.dp))
            }

            OutlinedTextField(
                value = notes,
                onValueChange = { notes = it },
                label = { Text("Observações do exame (opcional)") },
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(12.dp))

            Button(
                onClick = {
                    if (creating) return@Button
                    creating = true
                    scope.launch {
                        val exam = container.examRepository.createExam(patientUuid, notes)
                        creating = false
                        navController.navigate(Routes.captureGuide(exam.uuid))
                    }
                },
                enabled = hasConsent && !creating,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (creating) "Criando…" else "Iniciar captura guiada")
            }

            Spacer(modifier = Modifier.height(12.dp))
            OutlinedButton(
                onClick = { navController.navigate(Routes.history(patientUuid)) },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Ver histórico de exames")
            }

            Spacer(modifier = Modifier.height(24.dp))
            Text(text = "Exames deste paciente", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))

            if (exams.isEmpty()) {
                Text(
                    text = "Nenhum exame registrado neste dispositivo.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }

            LazyColumn {
                items(exams, key = { it.uuid }) { exam ->
                    ExamRow(exam = exam) {
                        navController.navigate(Routes.results(exam.uuid))
                    }
                }
            }
        }
    }
}

@Composable
private fun ExamRow(exam: ExamEntity, onClick: () -> Unit) {
    val statusLabel = when (exam.status) {
        "processed" -> "Processado"
        "reviewed" -> "Revisado"
        else -> "Rascunho"
    }
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .clickable(onClick = onClick),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                text = "Exame de ${exam.createdAt.take(10)}",
                style = MaterialTheme.typography.titleSmall,
            )
            Text(
                text = "Status: $statusLabel",
                style = MaterialTheme.typography.bodySmall,
            )
            exam.notes?.let {
                Text(text = it, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
