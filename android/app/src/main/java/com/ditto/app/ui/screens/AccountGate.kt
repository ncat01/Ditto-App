package com.ditto.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ditto.app.core.LocalAccounts
import com.ditto.app.core.ServiceLocator
import com.ditto.app.navigation.DittoAppRoot
import com.ditto.app.ui.theme.DittoColors
import com.ditto.app.ui.theme.HandwritingStyle
import com.ditto.app.ui.components.DittoCard
import com.ditto.app.ui.components.DittoMark
import com.ditto.app.ui.components.PrimaryButton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

val LocalSignOut = staticCompositionLocalOf<() -> Unit> { {} }

@Composable
fun AccountGate() {
    val context = LocalContext.current.applicationContext
    val accounts = remember { LocalAccounts(context) }
    val connection=remember { com.ditto.app.core.BackendConnection(context).also { it.configure(true,com.ditto.app.BuildConfig.API_BASE_URL) } }
    var connected by remember { mutableStateOf(connection.enabled()) }
    var endpoint by remember { mutableStateOf(connection.endpoint()) }
    var user by remember { mutableStateOf(connection.session()?.let { "server:${it.userId}" }) }
    var onboarded by remember { mutableStateOf(accounts.onboardingDone()) }
    var step by remember { mutableIntStateOf(0) }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var signup by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var clockMessage by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    if (!onboarded) {
        val titles = listOf("Your work. Your credit.","Evidence before action.","You stay in control.")
        val bodies = listOf("Keep a private record of your original work. Connect Instagram to import your own videos.","Compare originals with suspected copies. Similarity helps you review evidence; it does not establish ownership or infringement.","Review every candidate and message before approving an action. Available services depend on your account and deployment.")
        val notes = listOf("made by you", "review the signal", "your final say")
        val gradients = listOf(
            listOf(DittoColors.LightBlue, DittoColors.BlueTint, DittoColors.AquaTint),
            listOf(DittoColors.SunshineTint, DittoColors.BlueTint, DittoColors.LightBlue),
            listOf(DittoColors.AquaTint, DittoColors.LightBlue, DittoColors.BlueTint)
        )
        Column(Modifier.fillMaxSize().safeDrawingPadding().padding(24.dp),verticalArrangement=Arrangement.Center) {
            Row(verticalAlignment=Alignment.CenterVertically) {
                Box(Modifier.size(58.dp).clip(RoundedCornerShape(20.dp)).background(DittoColors.Surface.copy(alpha=.90f)),contentAlignment=Alignment.Center) { DittoMark(size=48) }
                Spacer(Modifier.width(12.dp))
                Column { Text("DITTO",style=MaterialTheme.typography.titleLarge,color=DittoColors.TextPrimary); Text("Content credit, clearly.",style=MaterialTheme.typography.bodySmall,color=DittoColors.TextSecondary) }
            }
            Spacer(Modifier.height(28.dp))
            Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(30.dp)).background(Brush.linearGradient(gradients[step])).padding(26.dp)) {
                Text("${step+1} / 3",style=MaterialTheme.typography.labelLarge,color=DittoColors.DeepBlue)
                Spacer(Modifier.height(20.dp))
                Text(titles[step],style=MaterialTheme.typography.displayMedium,color=DittoColors.DeepBlue)
                Text(notes[step],style=HandwritingStyle,color=DittoColors.SecondaryBlue)
                Spacer(Modifier.height(12.dp))
                Text(bodies[step],style=MaterialTheme.typography.bodyLarge,color=DittoColors.TextSecondary)
            }
            Spacer(Modifier.height(20.dp))
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.Center) {
                repeat(3) { index -> Box(Modifier.padding(horizontal=4.dp).size(if(index==step) 24.dp else 8.dp,8.dp).clip(CircleShape).background(if(index==step) DittoColors.PrimaryBlue else DittoColors.Border)) }
            }
            Spacer(Modifier.height(24.dp))
            PrimaryButton(if(step<2) "Continue" else "Get started",onClick={ if(step<2) step++ else { accounts.finishOnboarding(); onboarded=true } },modifier=Modifier.fillMaxWidth())
        }
    } else if(user == null) {
        Column(Modifier.fillMaxSize().safeDrawingPadding().imePadding().verticalScroll(rememberScrollState()).padding(24.dp),verticalArrangement=Arrangement.Center) {
            Row(verticalAlignment=Alignment.CenterVertically) {
                DittoMark(size=64)
                Spacer(Modifier.width(10.dp))
                Column {
                    Text("ditto",style=MaterialTheme.typography.displayMedium,color=DittoColors.TextPrimary)
                    Text("Made by you. Credited to you.",style=HandwritingStyle.copy(fontSize=28.sp,lineHeight=30.sp),color=DittoColors.SecondaryBlue)
                }
            }
            Spacer(Modifier.height(24.dp))
            DittoCard(background=DittoColors.Surface.copy(alpha=.90f),borderColor=DittoColors.LightBlue,contentPadding=22) {
                Text(if(signup) "Create your account" else "Welcome back",style=MaterialTheme.typography.headlineMedium,color=DittoColors.TextPrimary)
                Spacer(Modifier.height(6.dp))
                Text("Sign in once, then connect Instagram from your guided setup.",style=MaterialTheme.typography.bodySmall,color=DittoColors.TextSecondary)
                Spacer(Modifier.height(20.dp))
                OutlinedTextField(email,{email=it},label={Text("Email")},singleLine=true,shape=RoundedCornerShape(16.dp),modifier=Modifier.fillMaxWidth())
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(password,{password=it},label={Text("Password")},singleLine=true,shape=RoundedCornerShape(16.dp),visualTransformation=PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth())
                error?.let { Text(it,color=MaterialTheme.colorScheme.error,modifier=Modifier.padding(top=12.dp)) }
                Spacer(Modifier.height(18.dp))
                PrimaryButton(if(busy) "Please wait…" else if(signup) "Sign up" else "Log in",enabled=!busy,onClick={ scope.launch { busy=true; error=null; val result=withContext(Dispatchers.IO) { runCatching { connection.configure(true,endpoint); "server:${connection.authenticate(email,password,signup)}" } }; result.onSuccess { user=it; password="" }.onFailure { error=safeCustomerMessage(it.message,"Couldn't sign in. Please try again.") }; busy=false } },modifier=Modifier.fillMaxWidth())
                TextButton(onClick={signup=!signup;error=null},modifier=Modifier.align(Alignment.CenterHorizontally)) { Text(if(signup) "Already have an account? Log in" else "Create an account") }
            }
            if(connected) TextButton(enabled=!busy && email.isNotBlank(),modifier=Modifier.align(Alignment.CenterHorizontally), onClick={
                scope.launch {
                    busy=true;error=null
                    try {
                        connection.configure(true,endpoint)
                        val response=withContext(Dispatchers.IO) {
                            com.ditto.app.core.BackendApi(connection.endpoint(),null).request("api/auth/recovery",org.json.JSONObject().put("email",email).toString())
                        }
                        error=org.json.JSONObject(response).getString("message")
                    } catch(e:kotlinx.coroutines.CancellationException) { throw e }
                    catch(e:Exception) { error=safeCustomerMessage(e.message,"Couldn't request a recovery email. Please try again later.") }
                    finally {busy=false}
                }
            }) {Text("Forgot password?")}
        }
    } else {
        key(user) {
            val tutorialAccount=user!!
            val tutorialEndpoint=if(connected) connection.endpoint() else "offline"
            var showTutorial by remember { mutableStateOf(!TutorialProgress.completed(context,tutorialAccount,tutorialEndpoint)) }
            var ready by remember { mutableStateOf(false) }
            val owner=remember(user) { object : androidx.lifecycle.ViewModelStoreOwner, androidx.lifecycle.HasDefaultViewModelProviderFactory {
                override val viewModelStore=androidx.lifecycle.ViewModelStore()
                override val defaultViewModelProviderFactory=androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.getInstance(context as android.app.Application)
                override val defaultViewModelCreationExtras=androidx.lifecycle.viewmodel.MutableCreationExtras().apply {
                    set(androidx.lifecycle.ViewModelProvider.AndroidViewModelFactory.APPLICATION_KEY,context as android.app.Application)
                }
            } }
            DisposableEffect(owner) { onDispose { owner.viewModelStore.clear() } }
            ServiceLocator.activateUser(user!!)
            LaunchedEffect(user) {
                withContext(Dispatchers.IO) {
                    val repository=ServiceLocator.repository(context)
                    if(repository is com.ditto.app.data.repository.RemoteDittoRepository) {
                        runCatching { repository.refresh() }.onFailure { repository.connectionError.value="Ditto couldn't update this page. We'll try again automatically." }
                    }
                }
                ready=true
            }
            if(showTutorial) CreatorTutorial(connected) {
                TutorialProgress.finish(context,tutorialAccount,tutorialEndpoint)
                showTutorial=false
            } else Column(Modifier.fillMaxSize().statusBarsPadding()) {
                if(connected && ready) {
                    val remote=ServiceLocator.repository(context) as com.ditto.app.data.repository.RemoteDittoRepository
                    val serverError by remote.connectionError.collectAsState()
                    serverError?.let {
                        DittoCard(modifier=Modifier.padding(horizontal=16.dp,vertical=6.dp),background=DittoColors.BlueTint,contentPadding=12) {
                            Text(customerServiceStatus(it),color=DittoColors.TextSecondary,style=MaterialTheme.typography.bodySmall)
                        }
                    }
                }
                clockMessage?.let { Text(it,modifier=Modifier.padding(horizontal=16.dp),style=MaterialTheme.typography.bodySmall) }
                Box(Modifier.weight(1f)) { if(ready) CompositionLocalProvider(androidx.lifecycle.viewmodel.compose.LocalViewModelStoreOwner provides owner,
                    LocalSignOut provides {
                        val old=connection.session()
                        connection.logout()
                        user=null;clockMessage=null;ServiceLocator.activateUser(null)
                        scope.launch(Dispatchers.IO) { if(old!=null) runCatching { com.ditto.app.core.BackendApi(old.endpoint,old.token).request("api/auth/logout","{}") } }
                    }) { DittoAppRoot() } else CircularProgressIndicator(modifier=Modifier.padding(32.dp)) }
            }
        }
    }
}
