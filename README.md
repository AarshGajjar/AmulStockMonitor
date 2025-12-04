# Amul Stock Monitor

This project provides a Python-based stock monitor for Amul products, designed to run periodically using GitHub Actions. It alerts you via [ntfy.sh](https://ntfy.sh/) when a specific product comes back in stock.

## Features

- Monitors specified Amul protein products (or all protein products).
- Sends push notifications to your phone via ntfy.sh when a product changes from "unavailable" to "available".
- Runs on a schedule using GitHub Actions.
- Manages state to avoid duplicate notifications for products already in stock.

## Setup

### 1. Local Development Environment

It's recommended to set up a Python virtual environment for development.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/<your-username>/<your-repo-name>.git
    cd AmulStock
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### 2. GitHub Pages and Configuration UI

This project includes a user-friendly UI to help you select which products to monitor. You'll need to enable GitHub Pages to use it.

1.  **Enable GitHub Pages**:
    *   In your GitHub repository, go to `Settings` > `Pages`.
    *   Under "Build and deployment", for the "Source", select `Deploy from a branch`.
    *   Set the "Branch" to `main` and the folder to `/ (root)`. Click `Save`.
    *   Your configuration UI will be live at `https://<your-username>.github.io/<your-repo-name>/` in a few minutes.

2.  **Run the Action First**: Before using the UI, you need the GitHub Action to run at least once to create the `stock_status.json` file which the UI reads from. You can wait for the first scheduled run or trigger it manually from the "Actions" tab.

### 3. GitHub Configuration (Secrets)

To run the monitor, you need to configure several secrets in your GitHub repository.

1.  Go to your GitHub repository on the web.
2.  Navigate to `Settings` > `Secrets and variables` > `Actions`.
3.  Click on `New repository secret` for each of the following:

    *   `PINCODE`: The 6-digit pincode for the Amul store you want to monitor (e.g., `400001`).
    *   `NTFY_TOPIC`: Your unique topic for [ntfy.sh](https://ntfy.sh/) notifications. You can use any random string.
    *   `TARGET_PRODUCTS`: **Use the Configuration UI (see below) to generate the value for this secret.**

### 4. Configuring Monitored Products (UI)

Instead of manually typing product names, use the GitHub Pages UI you just enabled.

1.  Navigate to your GitHub Pages URL: `https://<your-username>.github.io/<your-repo-name>/`.
2.  The page will display a checklist of all available Amul protein products.
3.  Check the boxes next to the products you want to monitor.
4.  Click the **"Generate Secret"** button.
5.  A text box will appear with a comma-separated string of your selected products. **Copy this entire string.**
6.  Go to your `TARGET_PRODUCTS` secret in your GitHub settings and **paste the copied string** as its value.

This is the easiest and safest way to manage your product list.

### 5. GitHub Actions Workflow

The monitoring schedule is defined in the `.github/workflows/stock_monitor.yml` file.

-   **Schedule**: By default, it runs hourly (`cron: '0 * * * *'`). You can modify the `cron` expression in this file to change the frequency.
-   **Manual Trigger**: You can also trigger the workflow manually from the "Actions" tab in your repository.

## Usage

1.  **Configure**: Set up GitHub Pages and all the required secrets (`PINCODE`, `NTFY_TOPIC`, `TARGET_PRODUCTS`) as described above.
2.  **Set up ntfy.sh**: Download the app and subscribe to your `NTFY_TOPIC`.

### Running Locally (for Testing)

You can run the script locally to test your configuration before pushing.

1.  Activate your virtual environment.
2.  Set the environment variables in your terminal:
    ```powershell
    # On Windows (PowerShell)
    $env:PINCODE="400001"
    $env:TARGET_PRODUCTS="amul high protein blueberry shake, 200 ml | pack of 8,amul high protein paneer, 400 g | pack of 2"
    $env:NTFY_TOPIC="your-ntfy-topic"
    python main.py
    ```
    ```bash
    # On macOS/Linux
    export PINCODE="400001"
    export TARGET_PRODUCTS="amul high protein blueberry shake, 200 ml | pack of 8,amul high protein paneer, 400 g | pack of 2"
    export NTFY_TOPIC="your-ntfy-topic"
    python main.py
    ```

## Troubleshooting

-   **UI shows "Error" or "Loading..."**: Make sure the GitHub Action has run at least once successfully and that the `stock_status.json` file exists in your repository.
-   **No notifications**: Check your `NTFY_TOPIC` secret and ensure your `ntfy.sh` app is subscribed to the correct topic. Review the GitHub Actions logs for errors.

---
`stock_status.json` is used by the GitHub Action and the configuration UI. Please do not modify or delete this file manually.
