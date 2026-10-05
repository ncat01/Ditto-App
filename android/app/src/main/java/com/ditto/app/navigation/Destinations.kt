package com.ditto.app.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Assignment
import androidx.compose.material.icons.outlined.Bolt
import androidx.compose.material.icons.outlined.GridView
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.ui.graphics.vector.ImageVector

object Routes {
    const val HOME = "home"
    const val CASES = "cases"
    const val SCAN = "scan"
    const val ACTIVITY = "activity"
    const val SETTINGS = "settings"
    const val CASE_DETAIL = "case/{caseId}"
    const val FOLLOW_UP = "followup"
    const val ANALYTICS = "analytics"
    const val LIKENESS = "likeness"

    fun caseDetail(id: String) = "case/$id"
}

data class TabDestination(
    val route: String,
    val label: String,
    val icon: ImageVector
)

val bottomTabs = listOf(
    TabDestination(Routes.HOME, "Home", Icons.Outlined.GridView),
    TabDestination(Routes.SCAN, "Originals", Icons.Outlined.Search),
    TabDestination(Routes.CASES, "Cases", Icons.AutoMirrored.Outlined.Assignment),
    TabDestination(Routes.ACTIVITY, "Activity", Icons.Outlined.Bolt),
    TabDestination(Routes.SETTINGS, "Profile", Icons.Outlined.Tune)
)
