# Name-Classify-API v2

A simple REST API that analyzes names and predicts demographic information. Give it a name, and it will tell you the likely gender, approximate age, and country of origin!

---

## 🎯 What Does This API Do?

This API takes a person's name and uses advanced algorithms to predict:

- **👤 Gender** - Is the name typically associated with male or female? (includes confidence score)
- **🎂 Age Group** - Is the person likely a child, teen, adult, or senior?
- **🌍 Country** - Where is this name most commonly used? (includes confidence score)

All predictions are based on global name databases and are updated each time a name is analyzed.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Required packages (see `requirements.txt`)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your database connection with the `DB_URI` environment variable
4. Run the application:
   ```bash
   python main.py
   ```

The API will start on `http://localhost:5000`

---

## 📚 How to Use the API

### 1️⃣ Analyze a Name (Create a Profile)

**What it does:** Submit a name and get demographic predictions about it. The API saves this information in a database.

**Endpoint:** `POST /api/profiles`

**You send:**
```json
{
  "name": "John"
}
```

**You get back:**
```json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b",
    "name": "John",
    "gender": "male",
    "gender_probability": 0.95,
    "sample_size": 50000,
    "age": 42,
    "age_group": "adult",
    "country_id": "US",
    "country_probability": 0.78,
    "created_at": "2025-04-17T14:30:00Z"
  }
}
```

**What each field means:**
- `id`: Unique identifier for this profile
- `name`: The name you submitted
- `gender`: "male" or "female"
- `gender_probability`: How confident (0.0 to 1.0, where 1.0 = 100% sure)
- `sample_size`: How many data points the gender prediction is based on
- `age`: Predicted average age associated with this name
- `age_group`: "child" (0-12), "teen" (13-19), "adult" (20-64), or "senior" (65+)
- `country_id`: Country code where this name is most common (e.g., "US", "GB")
- `country_probability`: Confidence in the country prediction

---

### 2️⃣ Retrieve a Specific Profile

**What it does:** Look up a profile you previously created by its ID.

**Endpoint:** `GET /api/profiles/{id}`

**Example request:**
```
GET /api/profiles/550e8400-e29b
```

**You get back:**
```json
{
  "status": "success",
  "data": {
    "id": "550e8400-e29b",
    "name": "John",
    "gender": "male",
    "gender_probability": 0.95,
    "sample_size": 50000,
    "age": 42,
    "age_group": "adult",
    "country_id": "US",
    "country_probability": 0.78,
    "created_at": "2025-04-17T14:30:00Z"
  }
}
```

---

### 3️⃣ Search Profiles with Filters

**What it does:** Find all profiles in the database that match certain criteria (like all females, or all adults).

**Endpoint:** `GET /api/profiles`

**Optional filters you can use:**
- `gender` - Filter by gender ("male" or "female")
- `country_id` - Filter by country code ("US", "GB", "FR", etc.)
- `age_group` - Filter by age group ("child", "teen", "adult", "senior")

**Example requests:**

Get all female profiles:
```
GET /api/profiles?gender=female
```

Get all profiles from the United States:
```
GET /api/profiles?country_id=US
```

Get all adult profiles:
```
GET /api/profiles?age_group=adult
```

Combine multiple filters:
```
GET /api/profiles?gender=male&country_id=US&age_group=adult
```

**You get back:**
```json
{
  "status": "success",
  "data": [
    {
      "id": "550e8400-e29b",
      "name": "John",
      "gender": "male",
      "gender_probability": 0.95,
      "sample_size": 50000,
      "age": 42,
      "age_group": "adult",
      "country_id": "US",
      "country_probability": 0.78,
      "created_at": "2025-04-17T14:30:00Z"
    },
    {
      "id": "660f8400-f29c",
      "name": "James",
      "gender": "male",
      "gender_probability": 0.92,
      "sample_size": 48000,
      "age": 38,
      "age_group": "adult",
      "country_id": "US",
      "country_probability": 0.81,
      "created_at": "2025-04-17T15:00:00Z"
    }
  ],
  "count": 2
}
```

---

### 4️⃣ Delete a Profile

**What it does:** Permanently remove a profile from the database using its ID.

**Endpoint:** `DELETE /api/profiles/{id}`

**Example request:**
```
DELETE /api/profiles/550e8400-e29b
```

**Success response (Profile was deleted):**
```json
{
  "status": "success",
  "message": "Profile with ID 550e8400-e29b has been deleted"
}
```

**Success response (Profile ID not found - no record to delete):**
```json
{
  "status": "success",
  "message": "No record with the Id was found"
}
```

---

## ✅ Valid Inputs

**Name field:**
- Must contain only letters (A-Z, a-z) and spaces
- Cannot be empty
- Examples: "John", "Mary Smith", "Ahmad", "José"

**Age groups** (for filtering):
- `child` - Ages 0-12
- `teen` - Ages 13-19
- `adult` - Ages 20-64
- `senior` - Ages 65+

---

## ⚠️ Common Errors & How to Fix Them

| Error | What it means | How to fix |
|-------|---------------|-----------|
| `Name field is required` | You didn't send a name | Make sure your JSON includes `"name": "value"` |
| `Name must contain only letters` | Your name has numbers or special characters | Remove numbers and special characters |
| `Profile with ID not found` | The ID doesn't exist in the database | Check that you're using a correct ID |
| `Invalid age_group` | You used an invalid age group | Only use: child, teen, adult, senior |
| `Error storing profile in database` | Database connection issue | Check your database is running and `DB_URI` is correct |

---

## 💡 Example Use Cases

**Use Case 1: Predict demographics for user sign-up**
- When a user enters their name during registration, use the API to auto-fill demographic data

**Use Case 2: Analyze market data**
- Analyze customer name lists to understand gender and geographic distribution

**Use Case 3: Personalized content**
- Customize user experience based on predicted age group and location

**Use Case 4: Research & analytics**
- Query profiles by filters to analyze naming patterns across countries or demographics