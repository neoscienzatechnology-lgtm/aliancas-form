package com.footscan.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val LightColors = lightColorScheme(
    primary = BrandPetrol,
    onPrimary = ClinicOnPrimary,
    primaryContainer = BrandTurquoise2,
    secondary = BrandTurquoise,
    onSecondary = BrandPetrolDark,
    tertiary = BrandGray,
    background = ClinicBackground,
    onBackground = ClinicOnBackground,
    surface = ClinicSurface,
    onSurface = ClinicOnBackground,
    error = BrandRed,
)

@Composable
fun FootScanTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        typography = Typography,
        content = content,
    )
}
