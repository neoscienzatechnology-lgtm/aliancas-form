package com.footscan.app.ui.screens

import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.widget.Toast
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
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.footscan.app.data.api.AsymmetryDto
import com.footscan.app.data.api.ExamDetailDto
import com.footscan.app.data.api.MeasuresDto
import com.footscan.app.data.local.SyncState
import com.footscan.app.di.AppContainer
import kotlinx.coroutines.delay

/**
 * Resultados: medidas calculadas pelo servidor (mm/cm²), assimetria E−D e
 * exportação do relatório PDF no navegador.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultsScreen(
    container: AppContainer,
    navController: NavHostController,
    examUuid: String,
) {
    val context = LocalContext.current
    val serverUrl by container.settings.serverUrl.collectAsState(initial = "")
    val token by container.settings.authToken.collectAsState(initial = null)
    val localCaptures by container.examRepository
        .observeCaptures(examUuid)
        .collectAsState(initial = emptyList())

    var detail by remember { mutableStateOf<ExamDetailDto?>(null) }
    var loading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var refreshCounter by remember { mutableIntStateOf(0) }

    val pendingCount = localCaptures.count { it.syncState == SyncState.PENDING }

    LaunchedEffect(examUuid, refreshCounter) {
        loading = true
        errorMessage = null
        // Aguarda o processamento no servidor: tenta algumas vezes enquanto
        // houver captura sem resultado.
        var attempts = 0
        while (attempts < 6) {
            attempts++
            try {
                val fetched = container.examRepository.fetchExamDetail(examUuid)
                detail = fetched
                val stillProcessing = fetched.captures.isEmpty() ||
                    fetched.captures.any { !it.processed && it.error == null }
                if (!stillProcessing) break
            } catch (e: Exception) {
                errorMessage = "Sem conexão com o servidor. O exame será enviado " +
                    "automaticamente quando houver rede."
                break
            }
            delay(3000)
        }
        loading = false
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Resultados") },
                navigationIcon = {
                    IconButton(onClick = { navController.popBackStack() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Voltar")
                    }
                },
                actions = {
                    IconButton(onClick = { refreshCounter++ }) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Atualizar")
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
            if (pendingCount > 0) {
                Text(
                    text = "$pendingCount captura(s) aguardando envio ao servidor…",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary,
                )
                Spacer(modifier = Modifier.height(8.dp))
            }

            if (loading) {
                Row {
                    CircularProgressIndicator(modifier = Modifier.height(20.dp))
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "  Processando no servidor…",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
                Spacer(modifier = Modifier.height(12.dp))
            }

            errorMessage?.let {
                Text(text = it, color = MaterialTheme.colorScheme.error)
                Spacer(modifier = Modifier.height(12.dp))
            }

            detail?.let { exam ->
                val bySide = exam.captures
                    .filter { it.view == "plantar" }
                    .associateBy { it.footSide }
                val left = bySide["left"]
                val right = bySide["right"]

                for ((sideLabel, capture) in listOf("Pé esquerdo" to left, "Pé direito" to right)) {
                    if (capture == null) continue
                    Text(text = sideLabel, style = MaterialTheme.typography.titleMedium)
                    Spacer(modifier = Modifier.height(4.dp))
                    if (capture.error != null) {
                        Text(
                            text = "Erro no processamento: ${capture.error}",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall,
                        )
                    } else if (capture.measures == null) {
                        Text(
                            text = "Aguardando processamento…",
                            style = MaterialTheme.typography.bodySmall,
                        )
                    } else {
                        if (!token.isNullOrBlank() && serverUrl.isNotBlank()) {
                            AsyncImage(
                                model = ImageRequest.Builder(context)
                                    .data("${serverUrl.trimEnd('/')}/api/captures/${capture.uuid}/overlay")
                                    .addHeader("Authorization", "Bearer $token")
                                    .crossfade(true)
                                    .build(),
                                contentDescription = "Overlay do $sideLabel",
                                contentScale = ContentScale.FillWidth,
                                modifier = Modifier.fillMaxWidth(),
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                        }
                        MeasuresTable(measures = capture.measures)
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                }

                exam.asymmetry?.let { asymmetry ->
                    AsymmetryCard(asymmetry)
                    Spacer(modifier = Modifier.height(16.dp))
                }

                Button(
                    onClick = {
                        // O relatório exige o header Authorization (Bearer JWT);
                        // baixa via DownloadManager em vez de abrir a URL no navegador.
                        val url = "${serverUrl.trimEnd('/')}/api/exams/$examUuid/report.pdf"
                        val request = DownloadManager.Request(Uri.parse(url))
                            .addRequestHeader("Authorization", "Bearer $token")
                            .setMimeType("application/pdf")
                            .setTitle("Relatório Palmilha Inteligente")
                            .setNotificationVisibility(
                                DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED,
                            )
                            .setDestinationInExternalPublicDir(
                                Environment.DIRECTORY_DOWNLOADS,
                                "relatorio_footscan_$examUuid.pdf",
                            )
                        val downloadManager =
                            context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
                        downloadManager.enqueue(request)
                        Toast.makeText(
                            context,
                            "Baixando relatório em Downloads…",
                            Toast.LENGTH_SHORT,
                        ).show()
                    },
                    enabled = !token.isNullOrBlank(),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Exportar relatório (PDF)")
                }
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Documento de apoio; não constitui diagnóstico.",
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }
}

private fun fmt(value: Double?): String =
    value?.let { "%.1f".format(it) } ?: "—"

@Composable
private fun MeasureRow(label: String, value: String) {
    Row(modifier = Modifier
        .fillMaxWidth()
        .padding(vertical = 4.dp)) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.weight(1f),
        )
        Text(text = value, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun MeasuresTable(measures: MeasuresDto) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            MeasureRow("Comprimento", "${fmt(measures.lengthMm)} mm")
            HorizontalDivider()
            MeasureRow("Largura do antepé", "${fmt(measures.forefootWidthMm)} mm")
            HorizontalDivider()
            MeasureRow("Largura do mediopé", "${fmt(measures.midfootWidthMm)} mm")
            HorizontalDivider()
            MeasureRow("Largura do calcanhar", "${fmt(measures.heelWidthMm)} mm")
            HorizontalDivider()
            MeasureRow("Área plantar", "${fmt(measures.plantarAreaCm2)} cm²")
            HorizontalDivider()
            MeasureRow("Ângulo do eixo", "${fmt(measures.axisAngleDeg)}°")
            if (measures.manuallyAdjusted) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Medidas ajustadas manualmente pelo profissional.",
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }
}

@Composable
private fun AsymmetryCard(asymmetry: AsymmetryDto) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                text = "Assimetria (esquerdo − direito)",
                style = MaterialTheme.typography.titleSmall,
            )
            Spacer(modifier = Modifier.height(8.dp))
            MeasureRow("Comprimento", "${fmt(asymmetry.lengthMm)} mm")
            HorizontalDivider()
            MeasureRow("Largura do antepé", "${fmt(asymmetry.forefootWidthMm)} mm")
            HorizontalDivider()
            MeasureRow("Largura do mediopé", "${fmt(asymmetry.midfootWidthMm)} mm")
            HorizontalDivider()
            MeasureRow("Largura do calcanhar", "${fmt(asymmetry.heelWidthMm)} mm")
            HorizontalDivider()
            MeasureRow("Área plantar", "${fmt(asymmetry.plantarAreaCm2)} cm²")
        }
    }
}
