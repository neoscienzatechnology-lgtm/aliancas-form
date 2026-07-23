package com.footscan.app.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.footscan.app.data.api.HistoryItemDto
import com.footscan.app.di.AppContainer
import com.footscan.app.ui.Routes

/**
 * Histórico do paciente: exames ordenados por data (asc no servidor; exibidos
 * do mais recente para o mais antigo) com deltas de comprimento entre exames.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(
    container: AppContainer,
    navController: NavHostController,
    patientUuid: String,
) {
    var items by remember { mutableStateOf<List<HistoryItemDto>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(patientUuid) {
        loading = true
        errorMessage = null
        try {
            items = container.examRepository.fetchHistory(patientUuid)
        } catch (e: Exception) {
            errorMessage = "Não foi possível carregar o histórico. Verifique a conexão."
        }
        loading = false
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Histórico de exames") },
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
            if (loading) {
                CircularProgressIndicator()
            }
            errorMessage?.let {
                Text(text = it, color = MaterialTheme.colorScheme.error)
            }
            if (!loading && errorMessage == null && items.isEmpty()) {
                Text(
                    text = "Nenhum exame no histórico deste paciente.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            }

            // Servidor retorna em ordem ascendente; exibimos do mais recente.
            val ordered = items.reversed()
            LazyColumn {
                itemsIndexed(ordered, key = { _, item -> item.examUuid }) { index, item ->
                    val previous = ordered.getOrNull(index + 1)
                    HistoryRow(
                        item = item,
                        previous = previous,
                        onClick = { navController.navigate(Routes.results(item.examUuid)) },
                    )
                }
            }
        }
    }
}

@Composable
private fun HistoryRow(
    item: HistoryItemDto,
    previous: HistoryItemDto?,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .clickable(onClick = onClick),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                text = "Exame de ${item.createdAt?.take(10) ?: "—"}",
                style = MaterialTheme.typography.titleSmall,
            )
            Spacer(modifier = Modifier.height(4.dp))

            for (side in listOf("left" to "E", "right" to "D")) {
                val measures = item.measuresBySide[side.first]
                val length = measures?.lengthMm
                val prevLength = previous?.measuresBySide?.get(side.first)?.lengthMm
                val delta = if (length != null && prevLength != null) length - prevLength else null
                val deltaText = delta?.let {
                    " (Δ ${if (it >= 0) "+" else ""}${"%.1f".format(it)} mm)"
                } ?: ""
                Text(
                    text = "Pé ${side.second}: " +
                        (length?.let { "${"%.1f".format(it)} mm" } ?: "sem medida") +
                        deltaText,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
}
