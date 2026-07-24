package com.footscan.app.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.navigation.NavHostController
import com.footscan.app.di.AppContainer
import com.footscan.app.ui.Routes
import kotlinx.coroutines.launch
import java.io.File

// Placa: retângulo dos centros dos marcadores 250×380 mm + margem de 30 mm.
private const val PLATE_FRAME_WIDTH_MM = 310f
private const val PLATE_FRAME_HEIGHT_MM = 440f
private const val MARKER_RECT_WIDTH_MM = 250f
private const val MARKER_RECT_HEIGHT_MM = 380f
private const val MARKER_SIZE_MM = 40f

/**
 * Captura guiada: CameraX Preview + moldura da placa (4 marcadores ArUco) +
 * instruções em pt-BR. Captura por pé (E/D); a imagem é salva localmente e o
 * upload/processamento ocorre em segundo plano (SyncWorker).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CaptureGuideScreen(
    container: AppContainer,
    navController: NavHostController,
    examUuid: String,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()

    var hasCameraPermission by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
                PackageManager.PERMISSION_GRANTED
        )
    }
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> hasCameraPermission = granted }

    LaunchedEffect(Unit) {
        if (!hasCameraPermission) permissionLauncher.launch(Manifest.permission.CAMERA)
    }

    var footSide by remember { mutableStateOf("left") }
    var message by remember { mutableStateOf<String?>(null) }
    val imageCapture = remember { ImageCapture.Builder().build() }

    val captures by container.examRepository
        .observeCaptures(examUuid)
        .collectAsState(initial = emptyList())
    val leftDone = captures.any { it.footSide == "left" }
    val rightDone = captures.any { it.footSide == "right" }

    fun takePhoto() {
        val side = footSide
        val file = File(
            container.examRepository.capturesDir(),
            "${examUuid}_${side}_${System.currentTimeMillis()}.jpg",
        )
        val options = ImageCapture.OutputFileOptions.Builder(file).build()
        imageCapture.takePicture(
            options,
            ContextCompat.getMainExecutor(context),
            object : ImageCapture.OnImageSavedCallback {
                override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                    scope.launch {
                        container.examRepository.saveCapture(examUuid, side, file)
                        message = if (side == "left") {
                            "Pé esquerdo capturado. Agora capture o pé direito."
                        } else {
                            "Pé direito capturado."
                        }
                        if (side == "left" && !rightDone) footSide = "right"
                    }
                }

                override fun onError(exception: ImageCaptureException) {
                    message = "Falha ao capturar a imagem. Tente novamente."
                }
            },
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Captura guiada") },
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
                .padding(padding),
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
            ) {
                if (hasCameraPermission) {
                    AndroidView(
                        factory = { ctx ->
                            PreviewView(ctx).apply {
                                scaleType = PreviewView.ScaleType.FILL_CENTER
                                val providerFuture = ProcessCameraProvider.getInstance(ctx)
                                providerFuture.addListener({
                                    val provider = providerFuture.get()
                                    val preview = Preview.Builder().build().also {
                                        it.setSurfaceProvider(surfaceProvider)
                                    }
                                    provider.unbindAll()
                                    provider.bindToLifecycle(
                                        lifecycleOwner,
                                        CameraSelector.DEFAULT_BACK_CAMERA,
                                        preview,
                                        imageCapture,
                                    )
                                }, ContextCompat.getMainExecutor(ctx))
                            }
                        },
                        modifier = Modifier.fillMaxSize(),
                    )
                    PlateFrameOverlay(modifier = Modifier.fillMaxSize())
                } else {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp),
                        verticalArrangement = Arrangement.Center,
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text(
                            text = "É necessário permitir o uso da câmera para capturar as fotos.",
                            style = MaterialTheme.typography.bodyLarge,
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Button(onClick = { permissionLauncher.launch(Manifest.permission.CAMERA) }) {
                            Text("Permitir câmera")
                        }
                    }
                }
            }

            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "1. Encaixe a placa na moldura azul — os 4 marcadores devem aparecer inteiros.\n" +
                        "2. Apoie o pé descalço no centro da placa, sem cobrir os marcadores.\n" +
                        "3. Segure o celular paralelo à placa e evite sombras fortes.",
                    style = MaterialTheme.typography.bodySmall,
                )
                Spacer(modifier = Modifier.height(8.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(
                        selected = footSide == "left",
                        onClick = { footSide = "left" },
                        label = { Text(if (leftDone) "Pé esquerdo ✓" else "Pé esquerdo (E)") },
                    )
                    FilterChip(
                        selected = footSide == "right",
                        onClick = { footSide = "right" },
                        label = { Text(if (rightDone) "Pé direito ✓" else "Pé direito (D)") },
                    )
                }

                message?.let {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(text = it, style = MaterialTheme.typography.bodySmall)
                }
                Spacer(modifier = Modifier.height(12.dp))

                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = { takePhoto() },
                        enabled = hasCameraPermission,
                        modifier = Modifier.weight(1f),
                    ) {
                        Text(if (footSide == "left") "Capturar pé esquerdo" else "Capturar pé direito")
                    }
                    OutlinedButton(
                        onClick = {
                            navController.navigate(Routes.results(examUuid)) {
                                popUpTo(Routes.CAPTURE_GUIDE) { inclusive = true }
                            }
                        },
                        enabled = leftDone || rightDone,
                        modifier = Modifier.weight(1f),
                    ) {
                        Text("Concluir e processar")
                    }
                }
            }
        }
    }
}

/**
 * Moldura da placa de captura: contorno externo (placa com margem de 30 mm)
 * e os 4 quadrados dos marcadores ArUco nos cantos do retângulo 250×380 mm.
 */
@Composable
private fun PlateFrameOverlay(modifier: Modifier = Modifier) {
    Canvas(modifier = modifier) {
        val frameColor = Color(0xCC1565C0)
        val markerColor = Color(0xEE1565C0)

        val ratio = PLATE_FRAME_WIDTH_MM / PLATE_FRAME_HEIGHT_MM
        var frameHeight = size.height * 0.9f
        var frameWidth = frameHeight * ratio
        if (frameWidth > size.width * 0.9f) {
            frameWidth = size.width * 0.9f
            frameHeight = frameWidth / ratio
        }
        val left = (size.width - frameWidth) / 2f
        val top = (size.height - frameHeight) / 2f
        val mmX = frameWidth / PLATE_FRAME_WIDTH_MM
        val mmY = frameHeight / PLATE_FRAME_HEIGHT_MM

        drawRect(
            color = frameColor,
            topLeft = Offset(left, top),
            size = Size(frameWidth, frameHeight),
            style = Stroke(width = 4.dp.toPx()),
        )

        val markerPx = MARKER_SIZE_MM * mmX
        val centersX = listOf(30f * mmX, (30f + MARKER_RECT_WIDTH_MM) * mmX)
        val centersY = listOf(30f * mmY, (30f + MARKER_RECT_HEIGHT_MM) * mmY)
        for (cy in centersY) {
            for (cx in centersX) {
                drawRect(
                    color = markerColor,
                    topLeft = Offset(left + cx - markerPx / 2f, top + cy - markerPx / 2f),
                    size = Size(markerPx, markerPx),
                    style = Stroke(width = 3.dp.toPx()),
                )
            }
        }
    }
}
