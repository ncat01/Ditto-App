package com.ditto.app.navigation

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.ditto.app.ui.screens.ActivityScreen
import com.ditto.app.ui.screens.AnalyticsScreen
import com.ditto.app.ui.screens.CaseDetailScreen
import com.ditto.app.ui.screens.CasesScreen
import com.ditto.app.ui.screens.FollowUpScreen
import com.ditto.app.ui.screens.HomeScreen
import com.ditto.app.ui.screens.LikenessScreen
import com.ditto.app.ui.screens.ScanScreen
import com.ditto.app.ui.screens.SettingsScreen
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.viewmodel.DittoViewModel

@Composable
fun DittoAppRoot() {
    val navController = rememberNavController()
    val vm: DittoViewModel = viewModel(factory = DittoViewModel.Factory)
    val backStack by navController.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route
    val showBottomBar = currentRoute in bottomTabs.map { it.route }
    val toast by vm.toast.collectAsStateWithLifecycle()

    Scaffold(
        containerColor = DittoColors.Background,
        bottomBar = {
            AnimatedVisibility(
                visible = showBottomBar,
                enter = slideInVertically { it } + fadeIn(),
                exit = slideOutVertically { it } + fadeOut()
            ) {
                DittoBottomBar(
                    currentRoute = currentRoute,
                    onSelect = { route ->
                        navController.navigate(route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                )
            }
        }
    ) { padding ->
        Box(Modifier.fillMaxSize()) {
            NavHost(
                navController = navController,
                startDestination = Routes.HOME,
                modifier = Modifier
                    .fillMaxSize()
                    // Keep content clear of the status bar; the Scaffold handles the
                    // bottom bar inset via its own padding values.
                    
                    .padding(bottom = padding.calculateBottomPadding())
            ) {
                composable(Routes.HOME) {
                    HomeScreen(
                        vm = vm,
                        onOpenCase = { navController.navigate(Routes.caseDetail(it)) },
                        onSeeAllCases = { navController.navigate(Routes.CASES) },
                        onOpenFollowUp = { navController.navigate(Routes.FOLLOW_UP) },
                        onOpenAnalytics = { navController.navigate(Routes.ANALYTICS) },
                        onOpenScan = { navController.navigate(Routes.SCAN) }
                    )
                }
                composable(Routes.CASES) {
                    CasesScreen(
                        vm = vm,
                        onOpenCase = { navController.navigate(Routes.caseDetail(it)) }
                    )
                }
                composable(Routes.SCAN) {
                    ScanScreen(
                        onOpenCase = { navController.navigate(Routes.caseDetail(it)) }
                    )
                }
                composable(Routes.ACTIVITY) {
                    ActivityScreen(
                        vm = vm,
                        onOpenCase = { navController.navigate(Routes.caseDetail(it)) }
                    )
                }
                composable(Routes.SETTINGS) {
                    SettingsScreen(
                        vm = vm,
                        onOpenLikeness = { navController.navigate(Routes.LIKENESS) },
                        onOpenAnalytics = { navController.navigate(Routes.ANALYTICS) }
                    )
                }
                composable(
                    route = Routes.CASE_DETAIL,
                    arguments = listOf(navArgument("caseId") { type = NavType.StringType })
                ) { entry ->
                    val caseId = entry.arguments?.getString("caseId").orEmpty()
                    CaseDetailScreen(
                        caseId = caseId,
                        onBack = { navController.popBackStack() }
                    )
                }
                composable(Routes.FOLLOW_UP) {
                    FollowUpScreen(
                        vm = vm,
                        onBack = { navController.popBackStack() },
                        onOpenCase = { navController.navigate(Routes.caseDetail(it)) }
                    )
                }
                composable(Routes.ANALYTICS) {
                    AnalyticsScreen(vm = vm, onBack = { navController.popBackStack() })
                }
                composable(Routes.LIKENESS) {
                    LikenessScreen(onBack = { navController.popBackStack() })
                }
            }

            // Transient message bar
            AnimatedVisibility(
                visible = toast != null,
                enter = fadeIn() + slideInVertically { it / 2 },
                exit = fadeOut(),
                modifier = Modifier.align(Alignment.BottomCenter)
            ) {
                Box(
                    Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(DittoColors.DeepBlue)
                        .padding(horizontal = 14.dp, vertical = 12.dp)
                ) {
                    Text(
                        text = toast.orEmpty(),
                        style = MaterialTheme.typography.bodyMedium,
                        color = DittoColors.TextOnDark,
                        textAlign = TextAlign.Start
                    )
                }
            }
        }
    }

    LaunchedEffect(toast) {
        if (toast != null) {
            kotlinx.coroutines.delay(3200)
            vm.clearToast()
        }
    }
}

@Composable
private fun DittoBottomBar(currentRoute: String?, onSelect: (String) -> Unit) {
    Column {
        Box(
            Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(DittoColors.Border)
        )
        NavigationBar(
            containerColor = DittoColors.BackgroundAlt,
            tonalElevation = 0.dp
        ) {
            bottomTabs.forEach { tab ->
                val selected = currentRoute == tab.route
                NavigationBarItem(
                    selected = selected,
                    onClick = { if (!selected) onSelect(tab.route) },
                    icon = {
                        Icon(
                            imageVector = tab.icon,
                            contentDescription = tab.label,
                            modifier = Modifier.height(22.dp)
                        )
                    },
                    label = {
                        Text(
                            tab.label,
                            style = MaterialTheme.typography.labelMedium
                        )
                    },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = DittoColors.PrimaryBlue,
                        selectedTextColor = DittoColors.PrimaryBlue,
                        unselectedIconColor = DittoColors.TextTertiary,
                        unselectedTextColor = DittoColors.TextTertiary,
                        indicatorColor = DittoColors.LightBlue
                    )
                )
            }
        }
    }
}
