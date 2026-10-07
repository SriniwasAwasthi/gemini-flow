using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace GeminiFlow
{
    static class Program
    {
        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        private static extern void SwitchToThisWindow(IntPtr hWnd, bool fAltTab);

        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr hWnd);

        private const int SW_RESTORE = 9;

        [STAThread]
        static void Main(string[] args)
        {
            string defaultDir = @"E:\W c One Drive\Wisper";
            try
            {
                // 1. If dashboard window is already open and visible, instantly bring it to the foreground
                IntPtr existingHwnd = FindWindow(null, "Gemini Flow — Voice AI Settings & Dashboard");
                if (existingHwnd == IntPtr.Zero)
                {
                    existingHwnd = FindWindow(null, "Gemini Flow - Voice AI Settings & Dashboard");
                }
                if (existingHwnd != IntPtr.Zero && IsWindowVisible(existingHwnd))
                {
                    ShowWindow(existingHwnd, SW_RESTORE);
                    SwitchToThisWindow(existingHwnd, true);
                    SetForegroundWindow(existingHwnd);
                    return;
                }

                // 2. Locate main_standalone.py
                string exeDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');

                string scriptPath = Path.Combine(exeDir, "main_standalone.py");
                string workDir = exeDir;
                
                if (!File.Exists(scriptPath))
                {
                    scriptPath = Path.Combine(defaultDir, "main_standalone.py");
                    workDir = defaultDir;
                }

                if (!File.Exists(scriptPath))
                {
                    MessageBox.Show(
                        "Could not locate 'main_standalone.py'.\nTried:\n" + Path.Combine(exeDir, "main_standalone.py") + "\n" + scriptPath,
                        "Gemini Flow — Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                // 3. Locate Python executable
                string pythonPath = @"E:\PYTHON\pythonw.exe";
                if (!File.Exists(pythonPath))
                {
                    pythonPath = @"E:\PYTHON\python.exe";
                }

                // Forward arguments if any (e.g. --startup)
                string extraArgs = (args != null && args.Length > 0) ? " " + string.Join(" ", args) : "";

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = pythonPath;
                psi.Arguments = "\"" + scriptPath + "\"" + extraArgs;
                psi.WorkingDirectory = workDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.WindowStyle = ProcessWindowStyle.Hidden;

                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Error launching Gemini Flow:\n" + ex.Message,
                    "Gemini Flow — Launch Error",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }
    }
}
