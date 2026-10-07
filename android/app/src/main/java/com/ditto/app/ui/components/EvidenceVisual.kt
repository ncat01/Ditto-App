package com.ditto.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.ditto.app.ui.theme.DittoColors

/** Display only supplied media. Missing media is never replaced with generated evidence. */
@Composable
fun EvidenceVisual(seed: Int, modifier: Modifier = Modifier, localUri: String? = null,
                   label: String? = null, cornerRadius: Int = 8) {
    Box(modifier.background(DittoColors.BackgroundAlt),contentAlignment=Alignment.Center) {
        if(localUri != null) AsyncImage(model=localUri,contentDescription=label ?: "Private media",modifier=Modifier.fillMaxSize())
        else Text("Preview unavailable",style=MaterialTheme.typography.labelSmall,modifier=Modifier.padding(8.dp))
    }
}
