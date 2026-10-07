package com.ditto.app.ui.theme

import android.app.Activity
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat

private val DittoColorScheme = lightColorScheme(
    primary = DittoColors.PrimaryBlue,
    onPrimary = DittoColors.TextOnDark,
    primaryContainer = DittoColors.LightBlue,
    onPrimaryContainer = DittoColors.DeepBlue,
    secondary = DittoColors.SecondaryBlue,
    onSecondary = DittoColors.TextOnDark,
    secondaryContainer = DittoColors.BlueTint,
    onSecondaryContainer = DittoColors.DeepBlue,
    background = DittoColors.Background,
    onBackground = DittoColors.TextPrimary,
    surface = DittoColors.Surface,
    onSurface = DittoColors.TextPrimary,
    surfaceVariant = DittoColors.SurfaceMuted,
    onSurfaceVariant = DittoColors.TextSecondary,
    outline = DittoColors.Border,
    outlineVariant = DittoColors.BorderSubtle,
    error = DittoColors.Danger,
    onError = DittoColors.TextOnDark,
    errorContainer = DittoColors.DangerBg,
    onErrorContainer = DittoColors.Danger
)

/** Restrained radii — the brief explicitly rules out large pill-shaped cards. */
val DittoShapes = Shapes(
    extraSmall = RoundedCornerShape(8.dp),
    small = RoundedCornerShape(12.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(24.dp),
    extraLarge = RoundedCornerShape(30.dp)
)

@Composable
fun DittoTheme(content: @Composable () -> Unit) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = Color.Transparent.toArgb()
            window.navigationBarColor = DittoColors.Background.copy(alpha = .94f).toArgb()
            WindowCompat.getInsetsController(window, view).apply {
                isAppearanceLightStatusBars = true
                isAppearanceLightNavigationBars = true
            }
        }
    }
    MaterialTheme(
        colorScheme = DittoColorScheme,
        typography = DittoTypography,
        shapes = DittoShapes,
        content = content
    )
}
