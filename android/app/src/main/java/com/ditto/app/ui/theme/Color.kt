package com.ditto.app.ui.theme

import androidx.compose.ui.graphics.Color

/**
 * Ditto palette. Off-white paper, charcoal text, pink and sunrise accents.
 * Status hues are deliberately desaturated so they never dominate the identity.
 */
object DittoColors {
    // Foundation
    val Background = Color(0xFFFFFAF5)
    val BackgroundAlt = Color(0xFFFFF0EA)
    val Surface = Color(0xFFFFFFFF)
    val SurfaceMuted = Color(0xFFFFEBE8)
    val SurfaceSunken = Color(0xFFF5DCD9)

    // Brand accents (legacy property names retained for compatibility)
    val PrimaryBlue = Color(0xFFB72F65)
    val SecondaryBlue = Color(0xFFAD4939)
    val LightBlue = Color(0xFFFFD7E4)
    val DeepBlue = Color(0xFF63313C)
    val BlueTint = Color(0xFFFFEFF3)

    // Text
    val TextPrimary = Color(0xFF292A30)
    val TextSecondary = Color(0xFF575963)
    val TextTertiary = Color(0xFF686B75)
    val TextOnDark = Color(0xFFFFFAF5)

    // Lines
    val Border = Color(0xFFEBD9D2)
    val BorderSubtle = Color(0xFFF2E4DE)

    // Muted status
    val Success = Color(0xFF4A7C59)
    val SuccessBg = Color(0xFFE8EFE9)
    val Warning = Color(0xFF875322)
    val WarningBg = Color(0xFFF6EEE0)
    val Danger = Color(0xFF9B4A3F)
    val DangerBg = Color(0xFFF4E8E6)
    val Neutral = Color(0xFF6B7280)
    val NeutralBg = Color(0xFFEFEFEC)

    // Evidence placeholder gradients — one per palette seed, so seeded demo content
    // renders as distinct, plausible imagery without bundling photographs.
    val evidencePalettes: List<Pair<Color, Color>> = listOf(
        Color(0xFFAD4939) to Color(0xFFC4763F), // sunset
        Color(0xFF3E4C59) to Color(0xFF8A97A5), // studio
        Color(0xFF1F6F7A) to Color(0xFF7FB8B0), // coastal
        Color(0xFF6E5A3E) to Color(0xFFC3A87C), // market
        Color(0xFF8A5A3B) to Color(0xFFD9A05B), // rooftop
        Color(0xFF41567A) to Color(0xFF93A5C4),
        Color(0xFF4A6B4E) to Color(0xFF9DB89F)
    )

    fun evidencePalette(seed: Int): Pair<Color, Color> =
        evidencePalettes[((seed % evidencePalettes.size) + evidencePalettes.size) % evidencePalettes.size]
}
