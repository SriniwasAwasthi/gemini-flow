using System;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

namespace GeminiFlow
{
    static class Program
    {
        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
        private static extern int GetWindowTextLength(IntPtr hWnd);

        [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        private static extern void SwitchToThisWindow(IntPtr hWnd, bool fAltTab);

        [DllImport("user32.dll")]
        private static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        private static extern bool BringWindowToTop(IntPtr hWnd);

        private const int SW_RESTORE = 9;

        [STAThread]
        static void Main(string[] args)
        {
            string defaultDir = @"E:\W c One Drive\Wisper";
            try
            {
                // 0. If Gemini Flow is already running in background or system tray, notify it to SHOW window instantly
                try
                {
                    using (NamedPipeClientStream pipeClient = new NamedPipeClientStream(".", "GeminiFlow_SingleInstance_IPC", PipeDirection.Out))
                    {
                        pipeClient.Connect(350);
                        using (StreamWriter writer = new StreamWriter(pipeClient))
                        {
                            writer.WriteLine("SHOW");
                            writer.Flush();
                        }
                        // Running instance received SHOW and brought window to front. Exit immediately without spawning Python.
                        return;
                    }
                }
                catch
                {
                    // Instance not running or pipe not ready; continue with standard launch
                }

                // 1. If dashboard window is already open and visible, instantly bring it to the foreground
                IntPtr targetHwnd = IntPtr.Zero;
                EnumWindows(delegate(IntPtr hWnd, IntPtr lParam)
                {
                    if (IsWindowVisible(hWnd))
                    {
                        int len = GetWindowTextLength(hWnd);
                        if (len > 0)
                        {
                            StringBuilder sb = new StringBuilder(len + 1);
                            GetWindowText(hWnd, sb, sb.Capacity);
                            string title = sb.ToString();
                            if (title.IndexOf("Gemini Flow", StringComparison.OrdinalIgnoreCase) >= 0 &&
                                (title.IndexOf("Settings", StringComparison.OrdinalIgnoreCase) >= 0 ||
                                 title.IndexOf("Dashboard", StringComparison.OrdinalIgnoreCase) >= 0))
                            {
                                targetHwnd = hWnd;
                                return false; // Stop enumeration
                            }
                        }
                    }
                    return true;
                }, IntPtr.Zero);

                if (targetHwnd != IntPtr.Zero)
                {
                    ShowWindow(targetHwnd, SW_RESTORE);
                    BringWindowToTop(targetHwnd);
                    SwitchToThisWindow(targetHwnd, true);
                    SetForegroundWindow(targetHwnd);
                    return;
                }

                // 2. Locate main_standalone.py or main.py
                string exeDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
                string scriptPath = Path.Combine(exeDir, "main_standalone.py");
                if (!File.Exists(scriptPath))
                {
                    scriptPath = Path.Combine(exeDir, "app", "main.py");
                }
                if (!File.Exists(scriptPath))
                {
                    scriptPath = Path.Combine(exeDir, "main.py");
                }
                if (!File.Exists(scriptPath) && Directory.Exists(defaultDir))
                {
                    scriptPath = Path.Combine(defaultDir, "main_standalone.py");
                    if (!File.Exists(scriptPath))
                    {
                        scriptPath = Path.Combine(defaultDir, "app", "main.py");
                    }
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

                string projectDir = Path.GetDirectoryName(scriptPath);

                // 3. Locate Python executable dynamically across any laptop/PC
                string pythonPath = "";

                // Priority A: Project Virtual Environment (created by run.bat)
                string venvPythonw = Path.Combine(projectDir, "venv", "Scripts", "pythonw.exe");
                string venvPython = Path.Combine(projectDir, "venv", "Scripts", "python.exe");
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
                psi.WorkingDirectory = projectDir;
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
