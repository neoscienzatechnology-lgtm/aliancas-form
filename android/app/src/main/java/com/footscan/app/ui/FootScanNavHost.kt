package com.footscan.app.ui

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.footscan.app.di.AppContainer
import com.footscan.app.ui.screens.CaptureGuideScreen
import com.footscan.app.ui.screens.ExamNewScreen
import com.footscan.app.ui.screens.HistoryScreen
import com.footscan.app.ui.screens.LoginScreen
import com.footscan.app.ui.screens.PatientFormScreen
import com.footscan.app.ui.screens.PatientListScreen
import com.footscan.app.ui.screens.ResultsScreen
import com.footscan.app.ui.screens.SettingsScreen

/**
 * Fluxo principal (infográfico): Cadastro do paciente → Seleção do exame →
 * Captura guiada → Processamento → Resultados → Exportação do relatório (PDF).
 */
object Routes {
    const val LOGIN = "login"
    const val PATIENTS = "patients"
    const val PATIENT_FORM = "patient_form?patientUuid={patientUuid}"
    const val EXAM_NEW = "exam_new/{patientUuid}"
    const val CAPTURE_GUIDE = "capture_guide/{examUuid}"
    const val RESULTS = "results/{examUuid}"
    const val HISTORY = "history/{patientUuid}"
    const val SETTINGS = "settings"

    fun patientForm(patientUuid: String? = null): String =
        if (patientUuid == null) "patient_form" else "patient_form?patientUuid=$patientUuid"

    fun examNew(patientUuid: String): String = "exam_new/$patientUuid"
    fun captureGuide(examUuid: String): String = "capture_guide/$examUuid"
    fun results(examUuid: String): String = "results/$examUuid"
    fun history(patientUuid: String): String = "history/$patientUuid"
}

@Composable
fun FootScanNavHost(
    container: AppContainer,
    navController: NavHostController = rememberNavController(),
) {
    NavHost(navController = navController, startDestination = Routes.LOGIN) {

        composable(Routes.LOGIN) {
            LoginScreen(container = container, navController = navController)
        }

        composable(Routes.PATIENTS) {
            PatientListScreen(container = container, navController = navController)
        }

        composable(
            route = Routes.PATIENT_FORM,
            arguments = listOf(
                navArgument("patientUuid") {
                    type = NavType.StringType
                    nullable = true
                    defaultValue = null
                }
            ),
        ) { backStackEntry ->
            PatientFormScreen(
                container = container,
                navController = navController,
                patientUuid = backStackEntry.arguments?.getString("patientUuid"),
            )
        }

        composable(
            route = Routes.EXAM_NEW,
            arguments = listOf(navArgument("patientUuid") { type = NavType.StringType }),
        ) { backStackEntry ->
            ExamNewScreen(
                container = container,
                navController = navController,
                patientUuid = requireNotNull(backStackEntry.arguments?.getString("patientUuid")),
            )
        }

        composable(
            route = Routes.CAPTURE_GUIDE,
            arguments = listOf(navArgument("examUuid") { type = NavType.StringType }),
        ) { backStackEntry ->
            CaptureGuideScreen(
                container = container,
                navController = navController,
                examUuid = requireNotNull(backStackEntry.arguments?.getString("examUuid")),
            )
        }

        composable(
            route = Routes.RESULTS,
            arguments = listOf(navArgument("examUuid") { type = NavType.StringType }),
        ) { backStackEntry ->
            ResultsScreen(
                container = container,
                navController = navController,
                examUuid = requireNotNull(backStackEntry.arguments?.getString("examUuid")),
            )
        }

        composable(
            route = Routes.HISTORY,
            arguments = listOf(navArgument("patientUuid") { type = NavType.StringType }),
        ) { backStackEntry ->
            HistoryScreen(
                container = container,
                navController = navController,
                patientUuid = requireNotNull(backStackEntry.arguments?.getString("patientUuid")),
            )
        }

        composable(Routes.SETTINGS) {
            SettingsScreen(container = container, navController = navController)
        }
    }
}
