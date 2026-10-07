package com.ditto.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun LikenessScreen(onBack: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(24.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
        TextButton(onClick=onBack) { Text("Back") }
        Text("Likeness protection",style=MaterialTheme.typography.headlineMedium)
        Text("Not available",style=MaterialTheme.typography.titleMedium)
        Text("A validated face and manipulation detector has not been connected. Ditto does not infer manipulation from a matching face or similar video.")
        Text("Commercial-ad discovery is not connected. Your own Instagram imports and submitted-media comparisons remain separate features.")
    }
}
