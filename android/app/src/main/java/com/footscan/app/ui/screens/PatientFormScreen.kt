package com.footscan.app.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.footscan.app.di.AppContainer
import kotlinx.coroutines.launch

private val SEX_OPTIONS = listOf("" to "Não informado", "F" to "Feminino", "M" to "Masculino", "outro" to "Outro")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PatientFormScreen(
    container: AppContainer,
    navController: NavHostController,
    patientUuid: String?,
) {
    var name by remember { mutableStateOf("") }
    var birthDate by remember { mutableStateOf("") }
    var sex by remember { mutableStateOf("") }
    var document by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    var consentAccepted by remember { mutableStateOf(false) }
    var sexMenuExpanded by remember { mutableStateOf(false) }
    var saving by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    LaunchedEffect(patientUuid) {
        if (patientUuid != null) {
            container.patientRepository.getPatient(patientUuid)?.let { p ->
                name = p.name
                birthDate = p.birthDate.orEmpty()
                sex = p.sex.orEmpty()
                document = p.document.orEmpty()
                phone = p.phone.orEmpty()
                email = p.email.orEmpty()
                notes = p.notes.orEmpty()
                consentAccepted = p.consentAcceptedAt != null
            }
        }
    }

    fun save() {
        if (saving || name.isBlank()) return
        saving = true
        scope.launch {
            container.patientRepository.savePatient(
                uuid = patientUuid,
                name = name.trim(),
                birthDate = birthDate,
                sex = sex,
                document = document,
                phone = phone,
                email = email,
                notes = notes,
                consentAccepted = consentAccepted,
            )
            saving = false
            navController.popBackStack()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (patientUuid == null) "Novo paciente" else "Editar paciente") },
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
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
        ) {
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("Nome completo *") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = birthDate,
                onValueChange = { birthDate = it },
                label = { Text("Data de nascimento (AAAA-MM-DD)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(12.dp))

            ExposedDropdownMenuBox(
                expanded = sexMenuExpanded,
                onExpandedChange = { sexMenuExpanded = it },
            ) {
                OutlinedTextField(
                    value = SEX_OPTIONS.firstOrNull { it.first == sex }?.second ?: "Não informado",
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Sexo") },
                    trailingIcon = {
                        ExposedDropdownMenuDefaults.TrailingIcon(expanded = sexMenuExpanded)
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .menuAnchor(),
                )
                ExposedDropdownMenu(
                    expanded = sexMenuExpanded,
                    onDismissRequest = { sexMenuExpanded = false },
                ) {
                    SEX_OPTIONS.forEach { (value, label) ->
                        DropdownMenuItem(
                            text = { Text(label) },
                            onClick = {
                                sex = value
                                sexMenuExpanded = false
                            },
                        )
                    }
                }
            }
            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = document,
                onValueChange = { document = it },
                label = { Text("Documento (CPF/RG)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = phone,
                onValueChange = { phone = it },
                label = { Text("Telefone") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("E-mail") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(12.dp))

            OutlinedTextField(
                value = notes,
                onValueChange = { notes = it },
                label = { Text("Observações clínicas") },
                minLines = 3,
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(modifier = Modifier.height(16.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(
                    checked = consentAccepted,
                    onCheckedChange = { consentAccepted = it },
                )
                Text(
                    text = "O paciente leu e aceitou o termo de consentimento " +
                        "para tratamento de dados (LGPD) — versão v1.",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(start = 4.dp),
                )
            }
            Text(
                text = "O consentimento é obrigatório para criar exames.",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(start = 12.dp),
            )
            Spacer(modifier = Modifier.height(24.dp))

            Button(
                onClick = { save() },
                enabled = name.isNotBlank() && !saving,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (saving) "Salvando…" else "Salvar paciente")
            }
        }
    }
}
