package com.ditto.app.ui.screens

import android.content.Context
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import com.ditto.app.R
import com.ditto.app.ui.theme.DittoColors

object TutorialProgress {
    private fun key(account: String, endpoint: String) = java.security.MessageDigest.getInstance("SHA-256")
        .digest((endpoint+"|"+account).toByteArray()).joinToString("") { "%02x".format(it) }
    fun completed(context: Context, account: String, endpoint: String) = context.getSharedPreferences("creator_tutorial",0).getBoolean(key(account,endpoint),false)
    fun finish(context: Context, account: String, endpoint: String) { context.getSharedPreferences("creator_tutorial",0).edit().putBoolean(key(account,endpoint),true).apply() }
}

@Composable
fun CreatorTutorial(connected: Boolean, onFinish: () -> Unit) {
    var step by rememberSaveable { mutableIntStateOf(0) }
    val titles=listOf("Welcome to your creator space", "Bring in your original", "Scan, then check the evidence", "Shape your message", "You choose what happens")
    val bodies=listOf(
        if(connected) "Instagram import works with a Business or Creator account linked to your Ditto login. This test version needs the app owner to link it first. A private personal account can still use manual uploads."
        else "You are using the offline demo. Originals stay on this device. Instagram import and Gemini drafting are available in Connected test; manual uploads work here.",
        if(connected) "Open Originals, tap Load Instagram posts, then Import video. If Instagram is not linked, choose an image or video from your device instead. Imported videos appear in your library."
        else "Open Originals, add a title, then choose an image or video from your device. Select your upload or a sample original from the library.",
        "Select an original and tap Scan for matches. Open a case and compare both videos, publication dates, credit and permission. Discovery currently uses sample content, so results do not represent a search of all Instagram posts.",
        if(connected) "In a pending case, tap Draft with Gemini. Read the data-sharing prompt, generate a preview, edit it and tap Save draft. You can also use Edit draft without AI. Saving never sends a message."
        else "Open a pending case and tap Edit draft. Adjust the message and tone, then save. Saving a draft never sends it; you decide whether to approve the proposed action.",
        "Review the recipient and exact message before approving. You can edit or reject a proposal. This test records sandbox actions; it does not send real Instagram messages. Track case progress in Activity, and replay this guide from Profile."
    )
    val pictures=listOf(R.drawable.guide_connect,R.drawable.guide_import,R.drawable.guide_review,R.drawable.guide_draft,R.drawable.guide_approve)
    val descriptions=listOf("Illustration of a Creator profile linked to Ditto","Illustration of an original video entering your library","Illustration of two videos compared side by side","Illustration of an editable message draft","Illustration of a reviewed action with an approval check")
    Column(Modifier.fillMaxSize().background(DittoColors.Background).safeDrawingPadding().padding(24.dp)) {
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
            Text("YOUR DITTO GUIDE",style=MaterialTheme.typography.labelLarge,color=DittoColors.PrimaryBlue)
            TextButton(onClick=onFinish) { Text("Later") }
        }
        LinearProgressIndicator(progress={ (step+1)/5f },modifier=Modifier.fillMaxWidth(),color=DittoColors.PrimaryBlue)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            Spacer(Modifier.height(6.dp))
            Text("Step ${step+1} of 5",style=MaterialTheme.typography.labelMedium,color=DittoColors.TextSecondary)
            Image(painterResource(pictures[step]),contentDescription=descriptions[step],modifier=Modifier.fillMaxWidth().height(230.dp).clip(RoundedCornerShape(28.dp)).background(DittoColors.BackgroundAlt))
            Text(titles[step],style=MaterialTheme.typography.headlineMedium,color=DittoColors.TextPrimary)
            Text(bodies[step],style=MaterialTheme.typography.bodyLarge,color=DittoColors.TextPrimary)
            Text("Illustrated guide · ${if(connected) "Connected test" else "Offline demo"}",style=MaterialTheme.typography.bodySmall,color=DittoColors.TextSecondary)
        }
        Row(Modifier.fillMaxWidth().padding(top=12.dp),horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            if(step>0) OutlinedButton(onClick={step--},modifier=Modifier.weight(1f)) { Text("Back") }
            Button(onClick={if(step<4) step++ else onFinish()},modifier=Modifier.weight(1f)) { Text(if(step==4) "Let's go" else "Next") }
        }
    }
}
