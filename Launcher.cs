using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace GeminiFlow
{
    static class Program
    {
        [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
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
                IntPtr existingHwnd = FindWindow(null, "Gemini Flow - Voice AI Settings & Dashboard");
                if (existingHwnd == IntPtr.Zero)
                {
                    existingHwnd = FindWindow(null, "Gemini Flow — Voice AI Settings & Dashboard");
                }
                if (existingHwnd != IntPtr.Zero && IsWindowVisible(existingHwnd))
                {
                    ShowWindow(existingHwnd, SW_RESTORE);
                    SwitchToThisWindow(existingHwnd, true);
                    SetForegroundWindow(existingHwnd);
                    return;
                }

                // 2. Locate main_standalone.py or main.py
                string exeDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
                string scriptPath = Path.Combine(exeDir, "main_standalone.py");
                if (!File.Exists(scriptPath))
                {
                    scriptPath = Path.Combine(exeDir, "main.py");
                }
                if (!File.Exists(scriptPath) && Directory.Exists(defaultDir))
                {
                    scriptPath = Path.Combine(defaultDir, "main_standalone.py");
                    if (!File.Exists(scriptPath))
                    {
                        scriptPath = Path.Combine(defaultDir, "main.py");
                    }
                }

                if (!File.Exists(scriptPath))
                {
                    MessageBox.Show(
                        "Could not locate 'main_standalone.py' or 'main.py' in:\n" + exeDir + "\n\nPlease ensure all repository files are extracted completely.",
                        "Gemini Flow — Error",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                // 3. Locate Python executable dynamically across any laptop/PC
                string pythonPath = "";

                // Priority A: Project Virtual Environment (created by run.bat)
                string venvPythonw = Path.Combine(exeDir, "venv", "Scripts", "pythonw.exe");
                string venvPython = Path.Combine(exeDir, "venv", "Scripts", "python.exe");
                if (File.Exists(venvPythonw))
                {
                    pythonPath = venvPythonw;
                }
                else if (File.Exists(venvPython))
                {
                    pythonPath = venvPython;
                }
                // Priority B: Author's local development environment
                else if (File.Exists(@"E:\PYTHON\pythonw.exe"))
                {
                    pythonPath = @"E:\PYTHON\pythonw.exe";
                }
                else if (File.Exists(@"E:\PYTHON\python.exe"))
                {
                    pythonPath = @"E:\PYTHON\python.exe";
                }
                // Priority C: Standard Windows Python install directories
                else
                {
                    string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                    string pyDir = Path.Combine(localAppData, "Programs", "Python");
                    if (Directory.Exists(pyDir))
                    {
                        var dirs = Directory.GetDirectories(pyDir, "Python*");
                        Array.Sort(dirs);
                        Array.Reverse(dirs);
                        foreach (var d in dirs)
                        {
                            string pw = Path.Combine(d, "pythonw.exe");
                            string p = Path.Combine(d, "python.exe");
                            if (File.Exists(pw)) { pythonPath = pw; break; }
                            if (File.Exists(p)) { pythonPath = p; break; }
                        }
                    }
                }

                // Priority D: Fall back to system PATH
                if (string.IsNullOrEmpty(pythonPath))
                {
                    pythonPath = "pythonw.exe";
                }

                // Forward arguments if any (e.g. --startup)
                string extraArgs = (args != null && args.Length > 0) ? " " + string.Join(" ", args) : "";

                ProcessStartInfo psi = new ProcessStartInfo();
                psi.FileName = pythonPath;
                psi.Arguments = "\"" + scriptPath + "\"" + extraArgs;
                psi.WorkingDirectory = exeDir;
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.WindowStyle = ProcessWindowStyle.Hidden;

                Process.Start(psi);
            }
            catch (System.ComponentModel.Win32Exception)
            {
                MessageBox.Show(
                    "Python was not detected on your system.\n\nPlease double-click 'run.bat' once to automatically set up the virtual environment and install all dependencies from requirements.txt, or install Python 3.10+ from https://www.python.org/ (ensure 'Add Python to PATH' is checked).",
                    "Gemini Flow — Python Required",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
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
