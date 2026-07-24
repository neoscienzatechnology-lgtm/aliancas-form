# Regras ProGuard/R8 do FootScan (release usa isMinifyEnabled = false no scaffold).
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class com.footscan.app.data.api.** {
    *** Companion;
}
-keepclasseswithmembers class com.footscan.app.data.api.** {
    kotlinx.serialization.KSerializer serializer(...);
}
