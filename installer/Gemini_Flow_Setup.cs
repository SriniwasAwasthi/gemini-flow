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
        private CheckBox chkLaunchNow;
        private Panel pnlHeader;

        private string defaultInstallDir;

        public InstallerForm()
        {
            this.Text = "Gemini Flow — Setup Wizard";
            this.Size = new Size(580, 440);
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
            lblSubtitle.Text = "Next-Gen AI Voice Dictation & Real-Time Assistant (Sub-Second Latency)";
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
            chkDesktop.Location = new Point(28, 175);
            chkDesktop.AutoSize = true;
            chkDesktop.Font = new Font("Segoe UI", 9.5f);
            this.Controls.Add(chkDesktop);

            chkStartMenu = new CheckBox();
            chkStartMenu.Text = "Create a Start Menu shortcut";
            chkStartMenu.Checked = true;
            chkStartMenu.Location = new Point(28, 205);
            chkStartMenu.AutoSize = true;
            chkStartMenu.Font = new Font("Segoe UI", 9.5f);
            this.Controls.Add(chkStartMenu);

            chkLaunchNow = new CheckBox();
            chkLaunchNow.Text = "Launch Gemini Flow automatically when setup finishes";
            chkLaunchNow.Checked = true;
            chkLaunchNow.Location = new Point(28, 235);
            chkLaunchNow.AutoSize = true;
            chkLaunchNow.Font = new Font("Segoe UI", 9.5f);
            this.Controls.Add(chkLaunchNow);

            // Status label
            lblStatus = new Label();
            lblStatus.Text = "Ready to install. Click 'Install' to begin.";
            lblStatus.Font = new Font("Segoe UI", 9f, FontStyle.Italic);
            lblStatus.ForeColor = Color.FromArgb(148, 163, 184);
            lblStatus.Location = new Point(26, 275);
            lblStatus.Size = new Size(520, 20);
            this.Controls.Add(lblStatus);

            // Progress Bar
            progressBar = new ProgressBar();
            progressBar.Location = new Point(26, 300);
            progressBar.Size = new Size(518, 22);
            progressBar.Style = ProgressBarStyle.Continuous;
            this.Controls.Add(progressBar);

            // Install Button
            btnInstall = new Button();
            btnInstall.Text = "Install";
            btnInstall.Location = new Point(414, 345);
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
                    CopyDirectory(Path.Combine(sourceDir, "app"), Path.Combine(targetDir, "app"));

                    UpdateStatus("Copying pre-bundled offline models...", 50);
                    string srcModels = Path.Combine(sourceDir, "models");
                    if (Directory.Exists(srcModels))
                    {
                        CopyDirectory(srcModels, Path.Combine(targetDir, "models"));
                    }

                    UpdateStatus("Configuring application executables and icons...", 70);
                    string[] rootFiles = new string[] {
                        "Gemini Flow.exe", "Launcher.cs", "main.py", "main_standalone.py",
                        "app_icon.ico", "app_icon.png", "requirements.txt", "run.bat"
                    };

                    foreach (var rf in rootFiles)
                    {
                        string s = Path.Combine(sourceDir, rf);
                        if (File.Exists(s))
                        {
                            File.Copy(s, Path.Combine(targetDir, rf), true);
                        }
                    }

                    // Copy runtime if present
                    string srcRuntime = Path.Combine(sourceDir, "runtime");
                    if (Directory.Exists(srcRuntime))
                    {
                        UpdateStatus("Installing embedded Python runtime...", 85);
                        CopyDirectory(srcRuntime, Path.Combine(targetDir, "runtime"));
                    }

                    UpdateStatus("Creating Windows shortcuts and registry entries...", 92);
                    string targetExe = Path.Combine(targetDir, "Gemini Flow.exe");
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

                    RegisterUninstall(targetDir);

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

        private void RegisterUninstall(string installDir)
        {
            try
            {
                using (RegistryKey key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\GeminiFlow"))
                {
                    if (key != null)
                    {
                        key.SetValue("DisplayName", "Gemini Flow (AI Voice Assistant)");
                        key.SetValue("DisplayVersion", "2.0.0");
                        key.SetValue("Publisher", "Sriniwas Awasthi");
                        key.SetValue("InstallLocation", installDir);
                        key.SetValue("DisplayIcon", Path.Combine(installDir, "app_icon.ico"));
                        key.SetValue("NoModify", 1);
                        key.SetValue("NoRepair", 1);
                    }
                }
            }
            catch { }
        }
    }
}
