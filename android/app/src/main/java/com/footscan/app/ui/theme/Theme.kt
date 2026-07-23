package com.footscan.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColors = lightColorScheme(
    primary = ClinicBlue,
    onPrimary = ClinicOnPrimary,
    primaryContainer = ClinicBlueLight,
    secondary = ClinicBlueDark,
    onSecondary = ClinicOnPrimary,
    background = ClinicBackground,
    onBackground = ClinicOnBackground,
    surface = ClinicSurface,
    onSurface = ClinicOnBackground,
    error = ClinicError,
)

@Composable
fun FootScanTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        typography = Typography,
        content = content,
    )
}
