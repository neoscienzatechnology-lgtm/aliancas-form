package com.footscan.app.data.local

/**
 * Estado de sincronização de um registro local (armazenado como String no Room).
 */
object SyncState {
    const val PENDING = "PENDING"
    const val SYNCED = "SYNCED"
}
