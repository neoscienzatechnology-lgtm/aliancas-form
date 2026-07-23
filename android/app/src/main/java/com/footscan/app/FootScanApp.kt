package com.footscan.app

import android.app.Application
import com.footscan.app.di.AppContainer

class FootScanApp : Application() {

    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}
