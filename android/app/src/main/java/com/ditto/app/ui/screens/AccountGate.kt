package com.ditto.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.ditto.app.core.LocalAccounts
import com.ditto.app.core.ServiceLocator
import com.ditto.app.navigation.DittoAppRoot
import com.ditto.app.ui.theme.DittoColors
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun AccountGate() {
    val context = LocalContext.current.applicationContext
    val accounts = remember { LocalAccounts(context) }
    val connection=remember { com.ditto.app.core.BackendConnection(context).also { if(!com.ditto.app.BuildConfig.DEBUG) it.configure(true,com.ditto.app.BuildConfig.API_BASE_URL) } }
    var connected by remember { mutableStateOf(connection.enabled()) }
    var endpoint by remember { mutableStateOf(connection.endpoint()) }
    var user by remember { mutableStateOf(if(connection.enabled()) connection.session()?.let { "server:${it.userId}" } else accounts.session()) }
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
        val bodies = listOf("Protect originals and discover potential reposts in a reproducible offline demo.","Compare similarity, attribution and permission separately. Simulated manipulation evidence is always labelled.","Ditto proposes, you approve. Sandbox outreach records an action without sending it to a real platform.")
        Column(Modifier.fillMaxSize().background(DittoColors.Background).safeDrawingPadding().padding(28.dp),verticalArrangement=Arrangement.Center) {
            com.ditto.app.ui.components.DittoMark(size=88)
            Spacer(Modifier.height(24.dp))
            Text("DITTO   •   ${step+1} / 3",style=MaterialTheme.typography.labelLarge,color=DittoColors.PrimaryBlue)
            Spacer(Modifier.height(28.dp)); Text(titles[step],style=com.ditto.app.ui.theme.HandwritingStyle.copy(fontSize=androidx.compose.ui.unit.TextUnit(42f, androidx.compose.ui.unit.TextUnitType.Sp)),color=DittoColors.TextPrimary)
            Spacer(Modifier.height(20.dp)); Text(bodies[step],style=MaterialTheme.typography.bodyLarge)
            Spacer(Modifier.height(36.dp)); Button(onClick={ if(step<2) step++ else { accounts.finishOnboarding(); onboarded=true } },modifier=Modifier.fillMaxWidth()) { Text(if(step<2) "Continue" else "Get started") }
        }
    } else if(user == null) {
        Column(Modifier.fillMaxSize().background(DittoColors.Background).safeDrawingPadding().imePadding().verticalScroll(rememberScrollState()).padding(28.dp),verticalArrangement=Arrangement.Center) {
            com.ditto.app.ui.components.DittoMark(size=76)
            Text("ditto",style=MaterialTheme.typography.displayLarge,color=DittoColors.TextPrimary)
            Text("Made by you. Credited to you.",style=com.ditto.app.ui.theme.HandwritingStyle,color=DittoColors.SecondaryBlue)
            Spacer(Modifier.height(16.dp))
            Text(if(signup) "Create your account" else "Welcome back",style=MaterialTheme.typography.headlineMedium)
            Spacer(Modifier.height(12.dp)); Text(if(connected) "Cloud account • Your account and uploaded media are stored on this backend. Discovery remains synthetic and actions are sandboxed." else "Offline demo • Accounts and media stay on this device.",style=MaterialTheme.typography.bodySmall)
            if(com.ditto.app.BuildConfig.DEBUG) Row {
                TextButton(enabled=!busy,onClick={ connected=false; connection.configure(false,endpoint);error=null }) { Text(if(!connected) "✓ Offline demo" else "Offline demo") }
                TextButton(enabled=!busy,onClick={ connected=true;error=null }) { Text(if(connected) "✓ Cloud account" else "Cloud account") }
            }
            if(connected && com.ditto.app.BuildConfig.DEBUG) {
                OutlinedTextField(endpoint,{endpoint=it},label={Text("Backend URL")},placeholder={Text("https://your-codespace-8010.app.github.dev/")},singleLine=true,modifier=Modifier.fillMaxWidth())
                Text("Resume your Codespace and make test port 8010 public. Use a separate server account; offline accounts are not uploaded.",style=MaterialTheme.typography.bodySmall)
            }
            Spacer(Modifier.height(24.dp))
            OutlinedTextField(email,{email=it},label={Text("Email")},singleLine=true,modifier=Modifier.fillMaxWidth())
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(password,{password=it},label={Text("Password")},singleLine=true,visualTransformation=PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth())
            error?.let { Text(it,color=MaterialTheme.colorScheme.error,modifier=Modifier.padding(vertical=12.dp)) }
            Spacer(Modifier.height(20.dp))
            Button(enabled=!busy,onClick={ scope.launch { busy=true; error=null; val result=withContext(Dispatchers.IO) { runCatching { if(connected) { connection.configure(true,endpoint); "server:${connection.authenticate(email,password,signup)}" } else { connection.configure(false,endpoint); if(signup) accounts.signup(email,password) else accounts.login(email,password) } } }; result.onSuccess { user=it; password="" }.onFailure { error=it.message }; busy=false } },modifier=Modifier.fillMaxWidth()) { Text(if(busy) "Please wait…" else if(signup) "Sign up" else "Log in") }
            TextButton(onClick={signup=!signup;error=null}) { Text(if(signup) "Already have an account? Log in" else "Create an account") }
            if(connected) TextButton(enabled=!busy && email.isNotBlank(), onClick={
                scope.launch {
                    busy=true;error=null
                    try {
                        connection.configure(true,endpoint)
                        val response=withContext(Dispatchers.IO) {
                            com.ditto.app.core.BackendApi(connection.endpoint(),null).request("api/auth/recovery",org.json.JSONObject().put("email",email).toString())
                        }
                        error=org.json.JSONObject(response).getString("message")
                    } catch(e:kotlinx.coroutines.CancellationException) { throw e }
                    catch(e:Exception) { error=e.message ?: "Could not request recovery email." }
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
                        runCatching { repository.refresh() }.onFailure { repository.connectionError.value="Backend unavailable. Resume Codespace and check test port visibility." }
                    } else { repository.seedDemoData(false);com.ditto.app.core.FollowUpWorker.schedule(context,user!!);com.ditto.app.core.FollowUpWorker.checkDue(context,user!!) }
                }
                ready=true
            }
            if(showTutorial) CreatorTutorial(connected) {
                TutorialProgress.finish(context,tutorialAccount,tutorialEndpoint)
                showTutorial=false
            } else Column(Modifier.fillMaxSize()) {
                Row(Modifier.fillMaxWidth().statusBarsPadding().padding(horizontal=16.dp),horizontalArrangement=Arrangement.SpaceBetween) {
                    Text(if(connected) "CLOUD ACCOUNT" else "OFFLINE DEMO",color=DittoColors.PrimaryBlue,modifier=Modifier.padding(top=14.dp),style=MaterialTheme.typography.labelSmall)
                    if(connected) TextButton(onClick={ scope.launch { withContext(Dispatchers.IO) { runCatching { (ServiceLocator.repository(context) as com.ditto.app.data.repository.RemoteDittoRepository).refresh() }.onFailure { clockMessage="Backend unavailable. Resume your Codespace." } } } }) { Text("Refresh") }
                    else TextButton(onClick={ val id=user!!; scope.launch { val count=withContext(Dispatchers.IO) { com.ditto.app.core.DemoClock.advance(context,id);com.ditto.app.core.FollowUpWorker.checkDue(context,id) };clockMessage="Demo clock +7 days: $count due sandbox cases checked." } }) { Text("+7 days") }
                    TextButton(onClick={
                        if(connected) { val old=connection.session();connection.logout();scope.launch(Dispatchers.IO) { if(old!=null) runCatching { com.ditto.app.core.BackendApi(old.endpoint,old.token).request("api/auth/logout","{}") } } }
                        accounts.logout();user=null;clockMessage=null;ServiceLocator.activateUser(null)
                    }) { Text("Log out") }
                }
                if(connected && ready) {
                    val remote=ServiceLocator.repository(context) as com.ditto.app.data.repository.RemoteDittoRepository
                    val serverError by remote.connectionError.collectAsState()
                    serverError?.let { Text(it,color=DittoColors.Danger,modifier=Modifier.padding(horizontal=16.dp),style=MaterialTheme.typography.bodySmall) }
                }
                clockMessage?.let { Text(it,modifier=Modifier.padding(horizontal=16.dp),style=MaterialTheme.typography.bodySmall) }
                Box(Modifier.weight(1f)) { if(ready) CompositionLocalProvider(androidx.lifecycle.viewmodel.compose.LocalViewModelStoreOwner provides owner) { DittoAppRoot() } else CircularProgressIndicator(modifier=Modifier.padding(32.dp)) }
            }
        }
    }
}
