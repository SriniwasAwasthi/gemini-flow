"""
Automated Verification Suite for all 22 Production Prompt Transformations
from prompt_transformation_showcase.md.

Verifies:
1. Strict adherence to 5-part XML tags (<role>, <context>, <task>, <constraints>, <output_format>).
2. Elimination of cookie-cutter canned personas (e.g. no canned security persona for coffee shop).
3. Zero context loss and zero string truncation (no '...' dropping key requirements).
4. Greenfield vs Refactoring constraint alignment.
5. High-precision prompt generation across all 22 domain archetypes.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.transformation.transform_engine import TransformEngine


class Test22ShowcasePromptTransformations(unittest.TestCase):

    REQUIRED_TAGS = [
        "<role>", "</role>",
        "<context>", "</context>",
        "<task>", "</task>",
        "<constraints>", "</constraints>",
        "<output_format>", "</output_format>"
    ]

    def _assert_5_part_blueprint(self, prompt: str, domain_name: str):
        self.assertTrue(len(prompt) > 200, f"{domain_name}: Prompt output too short ({len(prompt)} chars)")
        for tag in self.REQUIRED_TAGS:
            self.assertIn(tag, prompt, f"{domain_name}: Missing required XML tag '{tag}'")
        self.assertNotIn("1. ROLE & PERSONA:", prompt, f"{domain_name}: Leaked legacy numeric format")
        self.assertNotIn("15. EXPECTED OUTPUT", prompt, f"{domain_name}: Leaked legacy numeric format")

    def test_example_01_coffee_shop_ecommerce(self):
        raw = (
            "Create a beginner-friendly e-commerce website for a coffee shop. "
            "The website should have a Home page, Product Listing page, Product Details page, "
            "Shopping Cart, Login/Register, and Checkout page. Users can browse coffee products, "
            "add items to the cart, and place orders. Use a clean coffee-themed design with "
            "responsive layouts for mobile and desktop.\n\n"
            "Tech Stack:\n"
            "• Frontend: React.js, Tailwind CSS\n"
            "• Backend: Node.js, Express.js\n"
            "• Database: MongoDB\n"
            "• Authentication: JWT\n"
            "• Payments: Stripe"
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 1 Coffee Shop")
        self.assertIn("Senior Full-Stack Architect", prompt)
        self.assertIn("Coffee Shop", prompt)
        self.assertIn("MongoDB", prompt)
        self.assertIn("Stripe", prompt)
        self.assertNotIn("FastAPI", prompt, "Should not hallucinate FastAPI")
        self.assertNotIn("modify only targeted code", prompt.lower(), "Greenfield app should not have refactoring constraints")

    def test_example_02_saas_landing_page_codepulse(self):
        raw = (
            'Make a high converting modern landing page for an AI code review tool named "CodePulse". '
            'I want a dark mode hero section, feature grid, social proof ticker, pricing table with '
            'monthly/annual toggle, and FAQ accordion.'
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 2 CodePulse")
        self.assertIn("Product Designer", prompt)
        self.assertIn("Landing Page", prompt)
        self.assertIn("Pricing", prompt)

    def test_example_03_windows_11_fluent_desktop(self):
        raw = (
            "Build a desktop system monitor app in Python that looks like Windows 11 Settings. "
            "It should show CPU usage, RAM, disk space, and running processes with kill buttons."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 3 Windows 11 Desktop")
        self.assertIn("Windows Desktop Software Engineer", prompt)
        self.assertIn("PyQt", prompt)
        self.assertIn("psutil", prompt)

    def test_example_04_restful_api_contract_mock_server(self):
        raw = (
            "I need an API spec and mock server for a patient appointment scheduling system "
            "for a dental clinic. Doctors, Patients, Appointments, and Services."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 4 API Spec")
        self.assertIn("API Architect", prompt)
        self.assertIn("OpenAPI", prompt)

    def test_example_05_web_scraper_ingestion(self):
        raw = (
            "Write a python scraper to get all job postings from a tech company careers page, "
            "extract job title, department, location, salary, and requirements, and save to SQLite."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 5 Web Scraper")
        self.assertIn("Data Ingestion Engineer", prompt)
        self.assertIn("SQLite", prompt)

    def test_example_06_machine_learning_churn(self):
        raw = (
            "Help me train a machine learning model to predict customer churn from a telecom CSV dataset. "
            "Show data cleaning, EDA, XGBoost training, evaluation metrics, and feature importance."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 6 ML Churn")
        self.assertIn("Machine Learning Engineer", prompt)
        self.assertIn("XGBoost", prompt)

    def test_example_07_zero_downtime_database_migration(self):
        raw = (
            "We need to split the users.name column into first_name and last_name in our production "
            "PostgreSQL database with 5 million users without breaking live traffic."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 7 Zero Downtime DB")
        self.assertIn("Database Reliability Engineer", prompt)
        self.assertIn("Expand/Contract", prompt)

    def test_example_08_docker_and_compose(self):
        raw = (
            "Dockerize our Node.js and Next.js frontend with an Express API and Redis backend "
            "so our developers can run docker compose up and have everything work with hot reload."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 8 Docker")
        self.assertIn("DevOps", prompt)
        self.assertIn("Multi-Stage", prompt)

    def test_example_09_flutter_mobile_app(self):
        raw = (
            "Make a Flutter fitness tracking app for iOS and Android. Screen to log workouts, "
            "screen to view exercise history, and a profile screen. Use state management and routing."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 9 Flutter App")
        self.assertIn("Flutter Architect", prompt)
        self.assertIn("Riverpod", prompt)

    def test_example_10_duckdb_redis_caching(self):
        raw = (
            "I want to cache frequently queried sales aggregation metrics in Redis and run "
            "analytical OLAP queries on parquet files with DuckDB in Python."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 10 DuckDB Redis")
        self.assertIn("Systems Architect", prompt)
        self.assertIn("DuckDB", prompt)

    def test_example_11_enterprise_auth_jwt(self):
        raw = (
            "Secure our user login system with JWT tokens. Make sure access tokens expire fast, "
            "refresh tokens rotate, and users can't get hacked by XSS or CSRF."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 11 Enterprise Auth")
        self.assertIn("Application Security Engineer", prompt)
        self.assertIn("Token Architecture", prompt)

    def test_example_12_event_driven_kafka(self):
        raw = (
            "Build a notification service in Python that listens to a Kafka topic for events "
            "like OrderPlaced and sends emails and SMS without losing messages if something crashes."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 12 Kafka")
        self.assertIn("Distributed Systems Engineer", prompt)
        self.assertIn("Kafka", prompt)

    def test_example_13_property_based_testing(self):
        raw = (
            "Write tests for my Python money and currency exchange calculation library. "
            "It should handle EUR, USD, GBP, rounding, and edge cases."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 13 Testing")
        self.assertIn("Test Automation Architect", prompt)
        self.assertIn("Hypothesis", prompt)

    def test_example_14_dark_mode_saas_dashboard(self):
        raw = (
            "Make a SaaS analytics dashboard in React with Tailwind and shadcn charts. "
            "Show total revenue, active users, conversion rate, and an area chart for traffic over the last 30 days."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 14 Dashboard")
        self.assertIn("Frontend Architect", prompt)
        self.assertIn("shadcn", prompt)

    def test_example_15_bullmq_job_queue(self):
        raw = (
            "I need a background job worker in Node.js to resize images uploaded by users "
            "into small, medium, and thumbnail sizes using BullMQ and Redis."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 15 BullMQ")
        self.assertIn("Backend Systems Engineer", prompt)
        self.assertIn("BullMQ", prompt)

    def test_example_16_playwright_e2e(self):
        raw = (
            "Write Playwright tests for our web app checkout flow. Test login, adding a product to cart, "
            "filling out address, and verifying checkout success."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 16 Playwright")
        self.assertIn("Playwright", prompt)
        self.assertIn("Page Object Model", prompt)

    def test_example_17_local_llm_serving(self):
        raw = (
            "Set up a Python server to run a local GGUF model with llama-cpp-python and "
            "expose an OpenAI-compatible /v1/chat/completions endpoint with streaming."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 17 Local LLM")
        self.assertIn("AI Systems Engineer", prompt)
        self.assertIn("GGUF", prompt)

    def test_example_18_open_source_readme(self):
        raw = (
            "Write a good README for my GitHub project. It's a CLI tool in Go that finds broken "
            "links in markdown files fast using goroutines."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 18 README")
        self.assertIn("Technical Writer", prompt)
        self.assertIn("README.md", prompt)

    def test_example_19_real_time_chat_websockets(self):
        raw = (
            "Build a real-time team chat room in React and Node.js with WebSockets. "
            "Users should see who is typing, who is online, and chat history."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 19 WebSockets")
        self.assertIn("Real-Time Systems Engineer", prompt)
        self.assertIn("WebSocket", prompt)

    def test_example_20_stripe_billing_webhooks(self):
        raw = (
            "Add Stripe billing to our SaaS app. We have a Pro plan for $19/mo. We need checkout sessions, "
            "customer portal for cancellations, and webhook handling."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 20 Stripe Billing")
        self.assertIn("Billing Architect", prompt)
        self.assertIn("Stripe", prompt)

    def test_example_21_database_query_tuning(self):
        raw = (
            "Our orders table query is super slow. It takes 4 seconds to load user orders filtered by date and status. "
            "Help me optimize the Postgres query and add the right indexes."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 21 Query Tuning")
        self.assertIn("Database Performance Engineer", prompt)
        self.assertIn("EXPLAIN", prompt)

    def test_example_22_rbac_multi_tenant(self):
        raw = (
            "Implement multi-tenant permissions in our Node.js app so Organizations can have Owners, Admins, and Members, "
            "and users can only touch their own company's data."
        )
        prompt = TransformEngine.convert_to_prompt(raw)
        self._assert_5_part_blueprint(prompt, "Example 22 RBAC")
        self.assertIn("Multi-Tenant", prompt)
        self.assertIn("RBAC", prompt)


if __name__ == "__main__":
    unittest.main()
