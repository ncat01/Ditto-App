import java.net.URI

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.ditto.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.ditto.app"
        minSdk = 26
        targetSdk = 36
        versionCode = 17
        versionName = "1.8.8"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        // Backend base URL is injected at build time, never hardcoded in source.
        // Override with -PdittoApiBaseUrl=https://your-host/ or in local.properties.
        // 10.0.2.2 is how an emulator reaches the host's localhost. Port 8010 keeps
        // Ditto clear of the FastAPI-conventional 8000, which is often already taken.
        val apiBaseUrl = (project.findProperty("dittoApiBaseUrl") as String?)
            ?: "http://10.0.2.2:8010/"
        buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")
    }

    // Credentials belong in the operator environment, never in Gradle/source control.
    val releaseStore = System.getenv("DITTO_SIGNING_STORE_FILE")
    if (!releaseStore.isNullOrBlank()) {
        signingConfigs.create("production") {
            storeFile = file(releaseStore)
            storePassword = System.getenv("DITTO_SIGNING_STORE_PASSWORD")
            keyAlias = System.getenv("DITTO_SIGNING_KEY_ALIAS")
            keyPassword = System.getenv("DITTO_SIGNING_KEY_PASSWORD")
        }
    }
    gradle.taskGraph.whenReady {
        if (allTasks.any { it.name.contains("Release") }) {
            val productionUrl = project.findProperty("dittoApiBaseUrl") as String?
            val uri = productionUrl?.let { URI(it) }
            require(uri?.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null &&
                uri.query == null && uri.fragment == null && uri.path in listOf("", "/")) {
                "Release requires -PdittoApiBaseUrl=https://your-production-host/"
            }
            require(!releaseStore.isNullOrBlank() && file(releaseStore).isFile &&
                listOf("DITTO_SIGNING_STORE_PASSWORD", "DITTO_SIGNING_KEY_ALIAS", "DITTO_SIGNING_KEY_PASSWORD")
                    .all { !System.getenv(it).isNullOrBlank() }) {
                "Release requires a private production signing key and DITTO_SIGNING_* environment settings."
            }
        }
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfig = signingConfigs.findByName("production")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

ksp {
    arg("room.schemaLocation", "$projectDir/schemas")
}

dependencies {
    implementation("androidx.work:work-runtime-ktx:2.10.0")
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.splashscreen)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.material.icons.extended)
    debugImplementation(libs.androidx.ui.tooling)

    implementation(libs.androidx.navigation.compose)

    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    implementation(libs.androidx.datastore.preferences)

    implementation(libs.retrofit)
    implementation(libs.retrofit.serialization)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.android)

    implementation(libs.coil.compose)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
}

val checkRuntimeAssets by tasks.registering {
    val runtime = file("src/main")
    inputs.dir(runtime)
    doLast {
        val forbidden = listOf("DemoCorpus", "VideoCorpus", "MockDiscoveryProvider",
            "MockVerificationAgent", "MockActionPlanningAgent", "MockFollowUpAgent",
            "DemoClock", "Alex Morgan", "Simulate weekly follow-up", "Offline demo")
        val violations = runtime.walkTopDown().filter { it.isFile }.filter { source ->
            val relative = source.relativeTo(runtime).invariantSeparatorsPath
            relative.startsWith("assets/corpus/") || source.name.startsWith("tutorial_") ||
                (source.extension == "kt" && forbidden.any { source.readText().contains(it) })
        }.map { it.relativeTo(runtime).invariantSeparatorsPath }.toList()
        check(violations.isEmpty()) { "Synthetic runtime content forbidden: ${violations.joinToString()}" }
    }
}
tasks.named("preBuild") { dependsOn(checkRuntimeAssets) }
