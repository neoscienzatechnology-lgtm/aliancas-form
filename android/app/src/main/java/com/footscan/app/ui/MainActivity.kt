package com.footscan.app.ui

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.footscan.app.FootScanApp
import com.footscan.app.ui.theme.FootScanTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as FootScanApp).container
        setContent {
            FootScanTheme {
                FootScanNavHost(container = container)
            }
        }
    }
}
