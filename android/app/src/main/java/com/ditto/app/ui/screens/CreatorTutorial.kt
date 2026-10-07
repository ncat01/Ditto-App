package com.ditto.app.ui.screens

import android.content.Context
import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.ui.layout.ContentScale
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ditto.app.R
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.ui.theme.HandwritingStyle
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.DittoMark
import com.ditto.app.ui.components.PrimaryButton
import com.ditto.app.ui.components.SecondaryButton

object TutorialProgress {
    private fun key(account: String, endpoint: String) = java.security.MessageDigest.getInstance("SHA-256")
        .digest((endpoint+"|"+account).toByteArray()).joinToString("") { "%02x".format(it) }
    fun completed(context: Context, account: String, endpoint: String) = context.getSharedPreferences("creator_tutorial",0).getBoolean(key(account,endpoint),false)
    fun finish(context: Context, account: String, endpoint: String) { context.getSharedPreferences("creator_tutorial",0).edit().putBoolean(key(account,endpoint),true).apply() }
}

@Composable
fun CreatorTutorial(connected: Boolean, onFinish: () -> Unit) {
    var step by rememberSaveable { mutableIntStateOf(0) }
    val titles=listOf("Connect Instagram", "Add your originals", "Request a comparison", "Review your evidence", "Stay in control")
    val bodies=listOf(
        "Tap Continue with Instagram to sign in securely and connect your Business or Creator account. Ditto never asks for your Instagram password.",
        "Open Originals to import your Instagram posts or upload an image or video from your phone. Your library starts empty.",
        "Choose an original and submit a suspected copy to compare. Cases are created only when you request a comparison or an available search. Ditto does not scan all Instagram posts.",
        "Open your case to review measured similarities, sources and your notes. Similarity alone does not establish infringement or permission.",
        "Edit any proposed message and check the recipient before approving. You can dismiss a case or delete your account from Profile."
    )
    val labels=listOf("Connect", "Originals", "Compare", "Review", "Decide")
    val accents=listOf(DittoColors.AuraPink,DittoColors.AuraViolet,DittoColors.AuraAqua,DittoColors.AuraGold,DittoColors.SecondaryBlue)
    Column(Modifier.fillMaxSize().safeDrawingPadding().padding(horizontal=22.dp,vertical=16.dp)) {
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
            Row(verticalAlignment=Alignment.CenterVertically) {
                DittoMark(size=38)
                Spacer(Modifier.width(8.dp))
                Text("YOUR DITTO GUIDE",style=MaterialTheme.typography.labelLarge,color=DittoColors.DeepBlue)
            }
            TextButton(onClick=onFinish) { Text("Later") }
        }
        Row(Modifier.fillMaxWidth().padding(vertical=12.dp),horizontalArrangement=Arrangement.SpaceBetween) {
            labels.forEachIndexed { index,label ->
                Column(horizontalAlignment=Alignment.CenterHorizontally) {
                    Box(Modifier.size(if(index==step) 18.dp else 10.dp).clip(CircleShape).background(if(index<=step) accents[index] else DittoColors.Border))
                    Spacer(Modifier.height(4.dp))
                    Text(label,style=MaterialTheme.typography.labelSmall,color=if(index==step) DittoColors.TextPrimary else DittoColors.TextTertiary)
                }
            }
        }
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(14.dp)) {
            DittoCard(background=DittoColors.Surface.copy(alpha=.86f),borderColor=accents[step].copy(alpha=.34f),contentPadding=22) {
                Text("Step ${step+1} of 5",style=MaterialTheme.typography.labelMedium,color=accents[step])
                Spacer(Modifier.height(8.dp))
                Text(titles[step],style=MaterialTheme.typography.displaySmall,color=DittoColors.DeepBlue)
                Text(listOf("one secure connection","build your private library","choose what to check","look before you act","always your call")[step],style=HandwritingStyle.copy(fontSize=29.sp,lineHeight=31.sp),color=DittoColors.SecondaryBlue)
                Spacer(Modifier.height(10.dp))
                Text(bodies[step],style=MaterialTheme.typography.bodyLarge,color=DittoColors.TextSecondary)
            }
            if (step == 0) InstagramConnectionCard()
            else DittoCard(background=when(step) { 1->DittoColors.BlueTint;2->DittoColors.AquaTint;3->DittoColors.SunshineTint;else->DittoColors.LightBlue },borderColor=Color.Transparent) {
                Text(when(step) {1->"Upload from your phone or import your own connected Instagram media.";2->"Use reverse search or select a suspected copy. Ditto never invents a case.";3->"Every match stays unverified until you inspect the source and comparison.";else->"Nothing is sent automatically. Edit, dismiss or act only when you are ready."},style=MaterialTheme.typography.titleMedium,color=DittoColors.DeepBlue)
            }
        }
        Row(Modifier.fillMaxWidth().padding(top=12.dp),horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            if(step>0) SecondaryButton("Back",onClick={step--},modifier=Modifier.weight(1f))
            PrimaryButton(
                if (step == 4) "Let's go" else "Next",
                onClick = { if (step < 4) step += 1 else onFinish() },
                modifier = Modifier.weight(1f)
            )
        }
    }
}
