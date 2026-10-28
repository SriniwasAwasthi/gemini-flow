using System;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace GeminiFlowSetup
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new InstallerForm());
        }
    }

    public class InstallerForm : Form
    {
        private ProgressBar progressBar;
        private Label lblStatus;
        private Label lblTitle;
        private Label lblSubtitle;
        private TextBox txtPath;
        private Button btnBrowse;
        private Button btnInstall;
        private CheckBox chkDesktop;
        private CheckBox chkStartMenu;
        private CheckBox chkStartup;
        private CheckBox chkLaunchNow;
        private Panel pnlHeader;

        private string defaultInstallDir;

        public InstallerForm()
        {
            this.Text = "Gemini Flow — Setup Wizard";
            this.Size = new Size(580, 490);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = true;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(15, 23, 42); // #0F172A Dark Slate
            this.ForeColor = Color.FromArgb(248, 250, 252); // #F8FAFC

            try
            {
                if (File.Exists("app_icon.ico"))
                {
                    this.Icon = new Icon("app_icon.ico");
                }
            }
            catch { }

            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            defaultInstallDir = Path.Combine(localAppData, "Programs", "GeminiFlow");

            InitializeComponents();
        }

        private void InitializeComponents()
        {
            // Header Panel
            pnlHeader = new Panel();
            pnlHeader.Dock = DockStyle.Top;
            pnlHeader.Height = 85;
            pnlHeader.BackColor = Color.FromArgb(30, 41, 59); // #1E293B

            lblTitle = new Label();
            lblTitle.Text = "Install Gemini Flow v2.0";
            lblTitle.Font = new Font("Segoe UI", 16, FontStyle.Bold);
            lblTitle.ForeColor = Color.FromArgb(248, 250, 252);
            lblTitle.Location = new Point(24, 15);
            lblTitle.AutoSize = true;

            lblSubtitle = new Label();
            lblSubtitle.Text = "Next-Gen AI Voice Dictation & Real-Time Assistant (Zero-Truncation Clean PC Ready)";
            lblSubtitle.Font = new Font("Segoe UI", 9.5f, FontStyle.Regular);
            lblSubtitle.ForeColor = Color.FromArgb(148, 163, 184); // #94A3B8
            lblSubtitle.Location = new Point(26, 48);
            lblSubtitle.AutoSize = true;

            pnlHeader.Controls.Add(lblTitle);
            pnlHeader.Controls.Add(lblSubtitle);
            this.Controls.Add(pnlHeader);

            // Install Path Label
            Label lblDir = new Label();
            lblDir.Text = "Destination Folder:";
            lblDir.Font = new Font("Segoe UI", 9.5f, FontStyle.Bold);
            lblDir.Location = new Point(24, 105);
            lblDir.AutoSize = true;
            this.Controls.Add(lblDir);

            // Path Textbox
            txtPath = new TextBox();
            txtPath.Text = defaultInstallDir;
            txtPath.Location = new Point(26, 130);
            txtPath.Size = new Size(420, 26);
            txtPath.BackColor = Color.FromArgb(30, 41, 59);
            txtPath.ForeColor = Color.White;
            txtPath.BorderStyle = BorderStyle.FixedSingle;
            txtPath.Font = new Font("Segoe UI", 9.5f);
            this.Controls.Add(txtPath);

            // Browse Button
            btnBrowse = new Button();
            btnBrowse.Text = "Browse...";
            btnBrowse.Location = new Point(456, 128);
            btnBrowse.Size = new Size(88, 28);
            btnBrowse.FlatStyle = FlatStyle.Flat;
            btnBrowse.BackColor = Color.FromArgb(51, 65, 85);
            btnBrowse.ForeColor = Color.White;
            btnBrowse.Font = new Font("Segoe UI", 9f);
            btnBrowse.Click += (s, e) =>
            {
                using (FolderBrowserDialog fbd = new FolderBrowserDialog())
                {
                    fbd.SelectedPath = txtPath.Text;
                    if (fbd.ShowDialog() == DialogResult.OK)
                    {
                        txtPath.Text = fbd.SelectedPath;
                    }
                }
            };
            this.Controls.Add(btnBrowse);

            // Checkboxes
            chkDesktop = new CheckBox();
            chkDesktop.Text = "Create a Desktop shortcut";
            chkDesktop.Checked = true;
            chkDesktop.Location = new Point(28, 170);
            chkDesktop.AutoSize = true;
            chkDesktop.Font = new Font("Segoe UI", 9.5f);
            this.Controls.Add(chkDesktop);

            chkStartMenu = new CheckBox();
            chkStartMenu.Text = "Create a Start Menu shortcut";
            chkStartMenu.Checked = true;
            chkStartMenu.Location = new Point(28, 198);
            chkStartMenu.AutoSize = true;
            chkStartMenu.Font = new Font("Segoe UI", 9.5f);
            this.Controls.Add(chkStartMenu);

            chkStartup = new CheckBox();
            chkStartup.Text = "Start Gemini Flow automatically when Windows starts";
            chkStartup.Checked = false;
            chkStartup.Location = new Point(28, 226);
            chkStartup.AutoSize = true;
            chkStartup.Font = new Font("Segoe UI", 9.5f);
            this.Controls.Add(chkStartup);

            chkLaunchNow = new CheckBox();
            chkLaunchNow.Text = "Launch Gemini Flow automatically when setup finishes";
            chkLaunchNow.Checked = true;
            chkLaunchNow.Location = new Point(28, 254);
            chkLaunchNow.AutoSize = true;
            chkLaunchNow.Font = new Font("Segoe UI", 9.5f);
            this.Controls.Add(chkLaunchNow);

            // Status label
            lblStatus = new Label();
            lblStatus.Text = "Ready to install. Click 'Install' to begin.";
            lblStatus.Font = new Font("Segoe UI", 9f, FontStyle.Italic);
            lblStatus.ForeColor = Color.FromArgb(148, 163, 184);
            lblStatus.Location = new Point(26, 290);
            lblStatus.Size = new Size(520, 20);
            this.Controls.Add(lblStatus);

            // Progress Bar
            progressBar = new ProgressBar();
            progressBar.Location = new Point(26, 315);
            progressBar.Size = new Size(518, 22);
            progressBar.Style = ProgressBarStyle.Continuous;
            this.Controls.Add(progressBar);

            // Install Button
            btnInstall = new Button();
            btnInstall.Text = "Install";
            btnInstall.Location = new Point(414, 390);
            btnInstall.Size = new Size(130, 36);
            btnInstall.FlatStyle = FlatStyle.Flat;
            btnInstall.BackColor = Color.FromArgb(99, 102, 241); // #6366F1 Indigo Accent
            btnInstall.ForeColor = Color.White;
            btnInstall.Font = new Font("Segoe UI", 10.5f, FontStyle.Bold);
            btnInstall.Click += BtnInstall_Click;
            this.Controls.Add(btnInstall);
        }

        private void BtnInstall_Click(object sender, EventArgs e)
        {
            btnInstall.Enabled = false;
            btnBrowse.Enabled = false;
            txtPath.Enabled = false;
            chkDesktop.Enabled = false;
            chkStartMenu.Enabled = false;
            chkStartup.Enabled = false;
            chkLaunchNow.Enabled = false;

            string targetDir = txtPath.Text.Trim();

            Thread t = new Thread(() =>
            {
                try
                {
                    UpdateStatus("Creating destination directory...", 10);
                    if (!Directory.Exists(targetDir))
                    {
                        Directory.CreateDirectory(targetDir);
                    }

                    string sourceDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');

                    UpdateStatus("Copying core application files...", 25);
                    string srcApp = Path.Combine(sourceDir, "app");
                    if (!Directory.Exists(srcApp) && Directory.Exists(Path.Combine(sourceDir, "..", "app")))
                    {
                        srcApp = Path.Combine(sourceDir, "..", "app");
                    }
                    CopyDirectory(srcApp, Path.Combine(targetDir, "app"));

                    UpdateStatus("Copying pre-bundled offline models...", 45);
                    string srcModels = Path.Combine(sourceDir, "models");
                    if (!Directory.Exists(srcModels) && Directory.Exists(Path.Combine(sourceDir, "..", "models")))
                    {
                        srcModels = Path.Combine(sourceDir, "..", "models");
                    }
                    if (Directory.Exists(srcModels))
                    {
                        CopyDirectory(srcModels, Path.Combine(targetDir, "models"));
                    }

                    UpdateStatus("Installing isolated Python runtime...", 70);
                    string srcRuntime = Path.Combine(sourceDir, "runtime");
                    if (!Directory.Exists(srcRuntime) && Directory.Exists(Path.Combine(sourceDir, "..", "runtime")))
                    {
                        srcRuntime = Path.Combine(sourceDir, "..", "runtime");
                    }
                    if (Directory.Exists(srcRuntime))
                    {
                        CopyDirectory(srcRuntime, Path.Combine(targetDir, "runtime"));
                    }

                    UpdateStatus("Configuring application executables and icons...", 85);
                    string[] rootFiles = new string[] {
                        "Gemini Flow.exe", "Gemini_Flow.exe", "Launcher.cs", "main.py", "main_standalone.py",
                        "app_icon.ico", "app_icon.png", "requirements.txt", "run.bat"
                    };

                    foreach (var rf in rootFiles)
                    {
                        string s = Path.Combine(sourceDir, rf);
                        if (!File.Exists(s) && File.Exists(Path.Combine(sourceDir, "..", rf)))
                        {
                            s = Path.Combine(sourceDir, "..", rf);
                        }
                        if (File.Exists(s))
                        {
                            File.Copy(s, Path.Combine(targetDir, rf), true);
                        }
                    }

                    UpdateStatus("Creating Windows shortcuts, startup config, and uninstaller...", 92);
                    string targetExe = Path.Combine(targetDir, "Gemini Flow.exe");
                    if (!File.Exists(targetExe) && File.Exists(Path.Combine(targetDir, "Gemini_Flow.exe")))
                    {
                        targetExe = Path.Combine(targetDir, "Gemini_Flow.exe");
                    }
                    string iconPath = Path.Combine(targetDir, "app_icon.ico");

                    if (chkDesktop.Checked)
                    {
                        CreateShortcut(
                            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "Gemini Flow.lnk"),
                            targetExe, targetDir, iconPath, "Gemini Flow — AI Voice Assistant"
                        );
                    }

                    if (chkStartMenu.Checked)
                    {
                        string startMenu = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), "Gemini Flow");
                        if (!Directory.Exists(startMenu)) Directory.CreateDirectory(startMenu);
                        CreateShortcut(
                            Path.Combine(startMenu, "Gemini Flow.lnk"),
                            targetExe, targetDir, iconPath, "Gemini Flow — AI Voice Assistant"
                        );
                    }

                    if (chkStartup.Checked)
                    {
                        try
                        {
                            using (RegistryKey runKey = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run", true))
                            {
                                if (runKey != null)
                                {
                                    runKey.SetValue("GeminiFlow", "\"" + targetExe + "\" --startup");
                                }
                            }
                        }
                        catch { }
                    }

                    RegisterUninstall(targetDir, targetExe);

                    UpdateStatus("Installation complete! Enjoy Gemini Flow.", 100);

                    this.Invoke((MethodInvoker)delegate
                    {
                        if (chkLaunchNow.Checked && File.Exists(targetExe))
                        {
                            Process.Start(new ProcessStartInfo
                            {
                                FileName = targetExe,
                                WorkingDirectory = targetDir
                            });
                        }

                        MessageBox.Show(
                            "Gemini Flow has been installed successfully!\n\nLocation: " + targetDir,
                            "Gemini Flow — Setup Finished",
                            MessageBoxButtons.OK,
                            MessageBoxIcon.Information
                        );
                        this.Close();
                    });
                }
                catch (Exception ex)
                {
                    this.Invoke((MethodInvoker)delegate
                    {
                        MessageBox.Show(
                            "An error occurred during installation:\n\n" + ex.Message,
                            "Gemini Flow — Setup Error",
                            MessageBoxButtons.OK,
                            MessageBoxIcon.Error
                        );
                        btnInstall.Enabled = true;
                    });
                }
            });
            t.IsBackground = true;
            t.Start();
        }

        private void UpdateStatus(string message, int progress)
        {
            if (this.InvokeRequired)
            {
                this.Invoke((MethodInvoker)delegate { UpdateStatus(message, progress); });
                return;
            }
            lblStatus.Text = message;
            progressBar.Value = Math.Min(100, Math.Max(0, progress));
        }

        private void CopyDirectory(string sourceDir, string destinationDir)
        {
            if (!Directory.Exists(sourceDir)) return;
            Directory.CreateDirectory(destinationDir);

            foreach (string file in Directory.GetFiles(sourceDir))
            {
                string targetFile = Path.Combine(destinationDir, Path.GetFileName(file));
                File.Copy(file, targetFile, true);
            }

            foreach (string subDir in Directory.GetDirectories(sourceDir))
            {
                string targetSubDir = Path.Combine(destinationDir, Path.GetFileName(subDir));
                CopyDirectory(subDir, targetSubDir);
            }
        }

        private void CreateShortcut(string shortcutPath, string targetPath, string workDir, string iconPath, string desc)
        {
            try
            {
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                dynamic shell = Activator.CreateInstance(shellType);
                dynamic shortcut = shell.CreateShortcut(shortcutPath);
                shortcut.TargetPath = targetPath;
                shortcut.WorkingDirectory = workDir;
                if (File.Exists(iconPath))
                {
                    shortcut.IconLocation = iconPath + ",0";
                }
                shortcut.Description = desc;
                shortcut.Save();
            }
            catch { }
        }

        private void RegisterUninstall(string installDir, string targetExe)
        {
            try
            {
                // Create robust uninstall batch script
                string uninstScript = Path.Combine(installDir, "uninstall.cmd");
                string scriptContent = "@echo off\r\n" +
                    "echo ====================================================\r\n" +
                    "echo            Gemini Flow - Uninstaller\r\n" +
                    "echo ====================================================\r\n" +
                    "echo Closing active Gemini Flow processes...\r\n" +
                    "taskkill /F /IM \"Gemini Flow.exe\" >nul 2>&1\r\n" +
                    "taskkill /F /IM \"Gemini_Flow.exe\" >nul 2>&1\r\n" +
                    "echo Removing Desktop and Start Menu shortcuts...\r\n" +
                    "del /Q \"%USERPROFILE%\\Desktop\\Gemini Flow.lnk\" >nul 2>&1\r\n" +
                    "rmdir /S /Q \"%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Gemini Flow\" >nul 2>&1\r\n" +
                    "echo Cleaning Windows registry configuration...\r\n" +
                    "reg delete \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\GeminiFlow\" /f >nul 2>&1\r\n" +
                    "reg delete \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\" /v \"GeminiFlow\" /f >nul 2>&1\r\n" +
                    "echo Removing Gemini Flow application files...\r\n" +
                    "cd \"%USERPROFILE%\"\r\n" +
                    "rmdir /S /Q \"" + installDir + "\" >nul 2>&1\r\n" +
                    "echo.\r\n" +
                    "echo Gemini Flow was successfully uninstalled from your PC.\r\n" +
                    "if not \"%1\"==\"/quiet\" pause\r\n";
                File.WriteAllText(uninstScript, scriptContent);

                using (RegistryKey key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\GeminiFlow"))
                {
                    if (key != null)
                    {
                        key.SetValue("DisplayName", "Gemini Flow (Zero-Truncation AI Voice Assistant)");
                        key.SetValue("DisplayVersion", "2.0.0");
                        key.SetValue("Publisher", "Sriniwas Awasthi");
                        key.SetValue("InstallLocation", installDir);
                        key.SetValue("DisplayIcon", Path.Combine(installDir, "app_icon.ico"));
                        key.SetValue("UninstallString", "\"" + uninstScript + "\"");
                        key.SetValue("QuietUninstallString", "\"" + uninstScript + "\" /quiet");
                        key.SetValue("NoModify", 1);
                        key.SetValue("NoRepair", 1);
                    }
                }
            }
            catch { }
        }
    }
}
