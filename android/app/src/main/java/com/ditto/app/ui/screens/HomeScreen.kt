package com.ditto.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ditto.app.ui.components.*
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.ui.theme.HandwritingStyle
import com.ditto.app.viewmodel.DittoViewModel

@Composable
fun HomeScreen(vm: DittoViewModel,onOpenCase:(String)->Unit,onSeeAllCases:()->Unit,
               onOpenFollowUp:()->Unit,onOpenAnalytics:()->Unit,onOpenScan:()->Unit) {
    val stats by vm.stats.collectAsStateWithLifecycle()
    val cases by vm.cases.collectAsStateWithLifecycle()
    val attention=remember(cases) { DittoViewModel.needingAttention(cases).take(3) }
    LazyColumn(Modifier.fillMaxSize().padding(horizontal=20.dp),
        contentPadding=PaddingValues(top=18.dp,bottom=34.dp),verticalArrangement=Arrangement.spacedBy(18.dp)) {
        item {
            Row(verticalAlignment=Alignment.CenterVertically) {
                Box(Modifier.size(52.dp).clip(RoundedCornerShape(18.dp)).background(DittoColors.Surface.copy(alpha=.88f)),contentAlignment=Alignment.Center) {
                    DittoMark(size=42)
                }
                Spacer(Modifier.width(12.dp))
                Column {
                    Text("DITTO",style=MaterialTheme.typography.titleLarge,color=DittoColors.TextPrimary)
                    Text("Your creator space",style=MaterialTheme.typography.bodySmall,color=DittoColors.TextSecondary)
                }
            }
        }
        item {
            Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(28.dp))
                .background(Brush.linearGradient(listOf(Color(0xFFCFC0FF),Color(0xFFFFC2DD),Color(0xFFBCEFEB))))
                .padding(horizontal=24.dp,vertical=26.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
                Eyebrow("Made by you",color=DittoColors.DeepBlue)
                Text("Your work deserves an echo.",style=MaterialTheme.typography.displayMedium,color=DittoColors.DeepBlue)
                Text("keep the credit.",style=HandwritingStyle,color=DittoColors.SecondaryBlue)
                Text("Add an original, search for possible copies, and decide what to do with the evidence.",
                    style=MaterialTheme.typography.bodyMedium,color=DittoColors.TextSecondary)
                Spacer(Modifier.height(4.dp))
                PrimaryButton("Search & compare",onOpenScan,Modifier.fillMaxWidth())
            }
        }
        item {
            Row(horizontalArrangement=Arrangement.spacedBy(12.dp)) {
                HomeTotal("Originals",stats.contentMonitored,DittoColors.AquaTint,DittoColors.AuraAqua,onOpenScan,Modifier.weight(1f))
                HomeTotal("Open cases",stats.openCases,DittoColors.SunshineTint,DittoColors.AuraGold,onSeeAllCases,Modifier.weight(1f))
            }
        }
        if(attention.isNotEmpty()) {
            item { SectionHeading("Ready for your review",trailing={
                Text("All cases",color=DittoColors.PrimaryBlue,modifier=Modifier.clickable(onClick=onSeeAllCases))
            }) }
            items(attention,key={it.id}) { CaseCard(case=it,onClick={onOpenCase(it.id)}) }
        } else {
            item {
                DittoCard(background=DittoColors.Surface.copy(alpha=.82f),borderColor=DittoColors.LightBlue) {
                    Eyebrow(if(cases.isEmpty()) "Ready when you are" else "All clear",color=DittoColors.Aqua)
                    Spacer(Modifier.height(4.dp))
                    Text(if(cases.isEmpty()) "Add your first original to begin searching."
                        else "Nothing needs your review right now.",
                        style=MaterialTheme.typography.titleMedium,color=DittoColors.TextPrimary)
                }
            }
        }
    }
}

@Composable
private fun HomeTotal(label:String,value:Int,color:Color,accent:Color,onClick:()->Unit,modifier:Modifier) {
    Column(modifier.clip(RoundedCornerShape(22.dp)).background(color).clickable(onClick=onClick).padding(18.dp)) {
        Box(Modifier.size(10.dp).clip(androidx.compose.foundation.shape.CircleShape).background(accent))
        Spacer(Modifier.height(10.dp))
        Text(value.toString(),style=MaterialTheme.typography.displaySmall,color=DittoColors.DeepBlue)
        Text(label,style=MaterialTheme.typography.bodyMedium,color=DittoColors.TextSecondary)
    }
}

internal fun com.ditto.app.domain.model.AgentKind.dotColor() = when(this) {
    com.ditto.app.domain.model.AgentKind.INGESTION -> DittoColors.TextTertiary
    com.ditto.app.domain.model.AgentKind.DISCOVERY -> DittoColors.SecondaryBlue
    com.ditto.app.domain.model.AgentKind.VERIFICATION -> DittoColors.PrimaryBlue
    com.ditto.app.domain.model.AgentKind.ACTION_PLANNING -> DittoColors.Warning
    com.ditto.app.domain.model.AgentKind.FOLLOW_UP -> DittoColors.DeepBlue
    com.ditto.app.domain.model.AgentKind.HUMAN -> DittoColors.Success
}
