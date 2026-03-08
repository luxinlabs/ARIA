# Platform Comparison Lab

## Overview

The Platform Comparison Lab is an AI-powered feature that enables interactive budget allocation analysis across Google Ads, Meta Ads, and TikTok Ads. It uses OpenAI to provide competitive insights, performance estimates, and optimization recommendations based on your brand's initialized strategy.

## Features

### 1. **Interactive Budget Allocation**
- Drag sliders to adjust budget percentages across three platforms
- Real-time budget calculations showing daily spend per platform
- Auto-normalization to ensure allocations sum to 100%

### 2. **AI-Powered Competitive Analysis**
OpenAI analyzes your allocation and provides:
- **Estimated Metrics**: Reach, CPA, CTR, CVR for each platform
- **Audience Fit Score**: How well each platform matches your target demographics
- **Creative Format Score**: Compatibility with each platform's ad formats
- **Competitive Intensity**: Market competition level (low/medium/high)
- **Platform Recommendations**: Specific guidance for each channel
- **Overall Strategy**: Holistic recommendation for your allocation
- **Risk Assessment**: Potential risks and mitigation strategies
- **Optimization Tips**: 3-5 actionable improvements

### 3. **Visual Performance Dashboard**
- Color-coded platform cards with emoji icons
- Progress bars for audience and creative fit scores
- Competition intensity badges
- Responsive grid layout

## How to Use

### Step 1: Initialize ARIA
Before using the comparison tool, ensure ARIA is initialized:
```bash
POST /aria/init
{
  "url": "https://yourbrand.com",
  "goal": "purchases",
  "budget_daily": 1000,
  "business_type": "B2C",
  "brand_name": "Your Brand"
}
```

### Step 2: Navigate to Comparison Lab
Click "Platform Comparison" in the navigation bar or visit `/compare`

### Step 3: Configure Campaign
1. Set **Total Daily Budget** (e.g., $1000)
2. Select **Campaign Goal** (purchases, leads, awareness, installs)
3. Adjust platform allocations using sliders:
   - Google Ads (Search, Display, YouTube)
   - Meta Ads (Facebook, Instagram)
   - TikTok Ads

### Step 4: Run AI Analysis
Click "Run AI Comparison" to get OpenAI-powered insights

### Step 5: Review Results
Analyze the detailed breakdown:
- Platform-specific metrics and scores
- Overall recommendation
- Risk assessment
- Optimization tips

## API Endpoint

### `POST /aria/compare`

**Request:**
```json
{
  "total_budget": 1000,
  "goal": "purchases",
  "allocations": [
    {"platform": "google", "percentage": 40},
    {"platform": "meta", "percentage": 40},
    {"platform": "tiktok", "percentage": 20}
  ]
}
```

**Response:**
```json
{
  "total_budget": 1000,
  "platform_metrics": [
    {
      "platform": "google",
      "estimated_reach": 50000,
      "estimated_cpa": 25.50,
      "estimated_ctr": 0.035,
      "estimated_cvr": 0.028,
      "audience_fit_score": 0.85,
      "creative_format_score": 0.78,
      "competitive_intensity": "high",
      "recommendation": "Strong fit for intent-driven searches..."
    }
  ],
  "overall_recommendation": "Your allocation favors Google and Meta...",
  "risk_assessment": "Moderate risk due to high competition...",
  "optimization_tips": [
    "Consider A/B testing creative formats on TikTok",
    "Allocate more budget to top-performing platform after 7 days"
  ]
}
```

## Technical Architecture

### Backend (`/backend/app/api/routes_aria.py`)
- **Endpoint**: `POST /aria/compare`
- **Dependencies**: OpenAI API, initialized ARIA state
- **Validation**: Ensures allocations sum to 100%
- **Context**: Uses brand DNA, target audience, and product info from ARIA memory
- **AI Model**: GPT-4o with JSON response format

### Frontend (`/frontend/src/components/PlatformComparison.jsx`)
- **Framework**: React with Framer Motion animations
- **Routing**: React Router (`/compare` route)
- **State Management**: React hooks for allocations and analysis
- **UI Components**: Lucide React icons, Tailwind CSS styling
- **Interactivity**: Range sliders with real-time percentage updates

### Data Models (`/backend/app/core/models.py`)
```python
class PlatformType(str, Enum):
    GOOGLE = "google"
    META = "meta"
    TIKTOK = "tiktok"

class PlatformAllocation(BaseModel):
    platform: PlatformType
    percentage: float  # 0-100

class ComparisonRequest(BaseModel):
    total_budget: float
    allocations: list[PlatformAllocation]
    goal: GoalType

class PlatformMetrics(BaseModel):
    platform: PlatformType
    estimated_reach: int
    estimated_cpa: float
    estimated_ctr: float
    estimated_cvr: float
    audience_fit_score: float  # 0-1
    creative_format_score: float  # 0-1
    competitive_intensity: str
    recommendation: str

class ComparisonResponse(BaseModel):
    total_budget: float
    platform_metrics: list[PlatformMetrics]
    overall_recommendation: str
    risk_assessment: str
    optimization_tips: list[str]
```

## Use Cases

### 1. **Initial Campaign Planning**
- Determine optimal platform mix before launching
- Understand expected performance across channels
- Identify potential risks early

### 2. **Budget Reallocation**
- Test different allocation scenarios
- Compare performance estimates
- Make data-driven reallocation decisions

### 3. **Competitive Research**
- Assess competitive intensity per platform
- Identify underutilized channels
- Find arbitrage opportunities

### 4. **Stakeholder Presentations**
- Generate AI-backed recommendations
- Visualize budget distribution
- Provide risk assessments

## Best Practices

1. **Start with Equal Distribution**: Begin with 33/33/33 split to see baseline recommendations
2. **Iterate Based on AI Feedback**: Adjust allocations based on optimization tips
3. **Consider Audience Fit**: Prioritize platforms with high audience fit scores
4. **Balance Risk**: Don't over-allocate to high-competition platforms
5. **Test Incrementally**: Make small allocation changes and re-analyze
6. **Align with Goals**: Different goals (awareness vs purchases) favor different platforms

## Limitations

- **Estimates Only**: Metrics are AI-generated predictions, not guaranteed results
- **Requires Initialization**: Must call `POST /aria/init` before using comparison
- **Static Analysis**: Does not account for real-time market changes
- **Platform Constraints**: Limited to Google, Meta, TikTok (expandable)

## Future Enhancements

- [ ] 3D visualization of platform performance space
- [ ] Historical comparison tracking
- [ ] Integration with live ARIA experiments
- [ ] Custom platform addition
- [ ] Export reports to PDF/CSV
- [ ] A/B test allocation scenarios
- [ ] Real-time market data integration
