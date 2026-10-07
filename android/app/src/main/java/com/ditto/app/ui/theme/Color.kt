package com.ditto.app.ui.theme

import androidx.compose.ui.graphics.Color

/** Bright creator palette: electric violet, magenta, aqua and sunlight. */
object DittoColors {
    // Foundation
    val Background = Color(0xFFF9F8FF)
    val BackgroundAlt = Color(0xFFF1EFFF)
    val Surface = Color(0xF7FFFFFF)
    val SurfaceMuted = Color(0xFFF0ECFF)
    val SurfaceSunken = Color(0xFFE5DFF7)

    // Brand accents (legacy property names retained for compatibility)
    val PrimaryBlue = Color(0xFF6738E8)
    val SecondaryBlue = Color(0xFFD9367A)
    val LightBlue = Color(0xFFE2D9FF)
    val DeepBlue = Color(0xFF301765)
    val BlueTint = Color(0xFFF4E9FF)
    val Aqua = Color(0xFF087F8C)
    val AquaTint = Color(0xFFD9F5F2)
    val Sunshine = Color(0xFFF2A51A)
    val SunshineTint = Color(0xFFFFEDC5)

    // Live background glow points.
    val AuraViolet = Color(0xFF8B5CF6)
    val AuraPink = Color(0xFFFF5AA5)
    val AuraAqua = Color(0xFF36D6C7)
    val AuraGold = Color(0xFFFFC857)

    // Text
    val TextPrimary = Color(0xFF211A35)
    val TextSecondary = Color(0xFF544D68)
    val TextTertiary = Color(0xFF716A84)
    val TextOnDark = Color(0xFFFFFFFF)

    // Lines
    val Border = Color(0xFFDCD5EF)
    val BorderSubtle = Color(0xFFEAE6F6)

    // Accessible status colours.
    val Success = Color(0xFF08775C)
    val SuccessBg = Color(0xFFDDF5EC)
    val Warning = Color(0xFF925700)
    val WarningBg = Color(0xFFFFEDC5)
    val Danger = Color(0xFFA32951)
    val DangerBg = Color(0xFFFFE1EA)
    val Neutral = Color(0xFF655E75)
    val NeutralBg = Color(0xFFEDEAF3)

    // Evidence placeholder gradients — one per palette seed, so seeded demo content
    // renders as distinct, plausible imagery without bundling photographs.
    val evidencePalettes: List<Pair<Color, Color>> = listOf(
        Color(0xFF6D3DE8) to Color(0xFFFF5AA5),
        Color(0xFF087F8C) to Color(0xFF42D9C8),
        Color(0xFFFF7A70) to Color(0xFFFFC857),
        Color(0xFF405DE6) to Color(0xFFC13584),
        Color(0xFF7C3AED) to Color(0xFF38BDF8),
        Color(0xFFD9367A) to Color(0xFFFF8A65),
        Color(0xFF0F766E) to Color(0xFFA3E635)
    )

    fun evidencePalette(seed: Int): Pair<Color, Color> =
        evidencePalettes[((seed % evidencePalettes.size) + evidencePalettes.size) % evidencePalettes.size]
}
