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
    var enlarged by remember { mutableStateOf(false) }
    val titles=listOf("Welcome to your creator space", "Bring in your original", "Scan, then check the evidence", "Shape your message", "You choose what happens")
    val bodies=listOf(
        if(connected) "Instagram import works with a Business or Creator account linked to your Ditto login. Tap Continue with Instagram below, sign in securely in your browser, then return here. Device uploads are also available."
        else "You are using the offline demo. Originals stay on this device. Instagram import and Gemini drafting are available with a cloud account; manual uploads work here.",
        if(connected) "Open Originals, tap Load Instagram posts, then Import video. If Instagram is not linked, choose an image or video from your device instead. Imported videos appear in your library."
        else "Open Originals, add a title, then choose an image or video from your device. Select your upload or a sample original from the library.",
        "Select your original to compare a suspected repost using image or video hashes. If web search is enabled, confirm sharing the image or sampled frames with Google to find possible sources. Review publication dates, credit and permission separately. Sample case screens below illustrate the evidence view.",
        if(connected) "In a pending case, tap Draft with Gemini. Read the data-sharing prompt, generate a preview, edit it and tap Save draft. You can also use Edit draft without AI. Saving never sends a message."
        else "Open a pending case and tap Edit draft. Adjust the message and tone, then save. Saving a draft never sends it; you decide whether to approve the proposed action.",
        if(connected) "Verify your email in Profile. When email delivery is enabled, enter a confirmed recipient and review the exact message before approving. SMTP acceptance does not confirm delivery or a reply. Optional follow-up reminders ask you to review the case; they do not send another email. Replay this guide from Profile."
        else "Review the proposed action and message. You can edit or reject a proposal. Offline approvals are simulated; they do not send a message. Track case progress in Activity, and replay this guide from Profile."
    )
    val pictures=listOf(R.drawable.guide_screen_originals,R.drawable.guide_screen_originals,R.drawable.guide_screen_review,R.drawable.guide_screen_draft,R.drawable.guide_screen_activity)
    val descriptions=listOf("Ditto Originals screen","Ditto upload and original library screen","Ditto case evidence screen with sample content","Ditto draft editor with a sample case","Ditto Activity screen with sample cases")
    if(enlarged) androidx.compose.ui.window.Dialog(onDismissRequest={enlarged=false},properties=androidx.compose.ui.window.DialogProperties(usePlatformDefaultWidth=false)) {
        Column(Modifier.fillMaxSize().background(DittoColors.Background).safeDrawingPadding()) {
            TextButton(onClick={enlarged=false}) {Text("Close screenshot")}
            Image(painterResource(pictures[step]),contentDescription=descriptions[step],contentScale=ContentScale.Fit,modifier=Modifier.fillMaxWidth().weight(1f))
        }
    }
    Column(Modifier.fillMaxSize().background(DittoColors.Background).safeDrawingPadding().padding(24.dp)) {
        Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
            Text("YOUR DITTO GUIDE",style=MaterialTheme.typography.labelLarge,color=DittoColors.PrimaryBlue)
            TextButton(onClick=onFinish) { Text("Later") }
        }
        LinearProgressIndicator(progress={ (step+1)/5f },modifier=Modifier.fillMaxWidth(),color=DittoColors.PrimaryBlue)
        Column(Modifier.weight(1f).verticalScroll(rememberScrollState()),verticalArrangement=Arrangement.spacedBy(16.dp)) {
            Spacer(Modifier.height(6.dp))
            Text("Step ${step+1} of 5",style=MaterialTheme.typography.labelMedium,color=DittoColors.TextSecondary)
            if (step == 0 && connected) InstagramConnectionCard()
            else Image(painterResource(pictures[step]),contentDescription=descriptions[step],contentScale=ContentScale.Fit,modifier=Modifier.fillMaxWidth().height(360.dp).clip(RoundedCornerShape(12.dp)).background(DittoColors.BackgroundAlt).clickable { enlarged=true })
            Text(titles[step],style=MaterialTheme.typography.headlineMedium,color=DittoColors.TextPrimary)
            Text(bodies[step],style=MaterialTheme.typography.bodyLarge,color=DittoColors.TextPrimary)
            if(step>0 || !connected) Text("Actual Ditto screen with example data ? tap to enlarge",style=MaterialTheme.typography.bodySmall,color=DittoColors.TextSecondary)
        }
        Row(Modifier.fillMaxWidth().padding(top=12.dp),horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            if(step>0) OutlinedButton(onClick={step--},modifier=Modifier.weight(1f)) { Text("Back") }
            Button(onClick={if(step<4) step++ else onFinish()},modifier=Modifier.weight(1f)) { Text(if(step==4) "Let's go" else "Next") }
        }
    }
}
