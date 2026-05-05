# Power BI Report Template - Conference Attendance

This template provides a comprehensive attendance tracking dashboard with automated deployment to Fabric workspace.

## 📊 Report Pages

### 1. Attendance Overview
**Purpose**: High-level metrics and visualizations

**Visuals**:
- **KPI Cards** (4 metrics):
  - Total Registrations
  - Total Attended  
  - Attendance Rate %
  - Average Session Rating

- **Donut Chart**: Attendance by Status
  - Attended (Green)
  - Registered (Blue)
  - No-show (Red)
  - Cancelled (Gray)

- **Bar Chart**: Session Popularity
  - Shows registration count per session
  - Sorted by popularity

- **Column Chart**: Rating Distribution
  - Histogram of session ratings 1-5

### 2. Attendee List
**Purpose**: Searchable, filterable list of all attendees

**Visual**:
- **Enhanced Table**:
  - Columns: First Name, Last Name, Email, Company, Job Title, Session, Status, Rating
  - Searchable and sortable
  - Conditional formatting:
    - Green background for "Attended"
    - Red background for "No-show"
    - Ratings >= 4 highlighted green
    - Ratings <= 2 highlighted red

### 3. Session Analytics
**Purpose**: Deep dive into session performance

**Visuals**:
- **Session Performance Table**:
  - Metrics: Registrations, Attended, Attendance %, Avg Rating
  - Grouped by session name

- **Treemap**: Attendees by Company
  - Size = number of attendees

- **Horizontal Bar Chart**: Job Title Distribution

- **Line Chart**: Check-in Trend Over Time

## 🔧 DAX Measures

Pre-configured measures included:

```dax
Total Registrations = COUNTROWS(conference_attendance)

Total Attended = COUNTROWS(FILTER(conference_attendance, [AttendanceStatus] = "Attended"))

Attendance Rate = DIVIDE([Total Attended], [Total Registrations], 0)

Average Session Rating = AVERAGE(conference_attendance[SessionRating])

Highly Rated Sessions = COUNTROWS(FILTER(conference_attendance, [SessionRating] >= 4))
```

## 🚀 Automated Deployment

### Option 1: Complete Automation (Recommended)

Deploy semantic model + report together:

```bash
python scripts/deploy_powerbi_report.py \
    --workspace-id "00bcfcd2-97d8-48b0-8ae4-67e7395ac373" \
    --lakehouse-name "ConferenceDataLakehouse" \
    --model-name "Conference Attendance Model" \
    --report-name "Conference Attendance Report"
```

This automatically:
1. ✅ Creates semantic model from Lakehouse
2. ✅ Deploys report template
3. ✅ Binds report to semantic model
4. ✅ Configures data refresh

### Option 2: Manual Creation in Power BI Desktop

1. **Open Power BI Desktop**
2. **Get Data** → **OneLake data hub**
3. **Connect** to `ConferenceDataLakehouse`
4. **Select** `conference_attendance` table
5. **Load** data

6. **Create Measures** (Modeling tab → New Measure):
   ```dax
   Total Registrations = COUNTROWS(conference_attendance)
   Total Attended = COUNTROWS(FILTER(conference_attendance, [AttendanceStatus] = "Attended"))
   Attendance Rate = DIVIDE([Total Attended], [Total Registrations], 0)
   Average Session Rating = AVERAGE(conference_attendance[SessionRating])
   ```

7. **Add Visuals** (see template JSON for layout)
   - Page 1: Overview with KPIs and charts
   - Page 2: Attendee list table
   - Page 3: Session analytics

8. **Apply Formatting**:
   - Theme colors: Blue (#3498DB), Green (#27AE60), Orange (#F39C12), Red (#E74C3C)
   - Background: Light gray (#F5F5F5)
   - Font: Segoe UI

9. **Save** as `Conference-Attendance-Report.pbix`

10. **Publish** to workspace

### Option 3: Deploy Existing .pbix File

If you already created a .pbix file:

```bash
python scripts/deploy_powerbi_report.py \
    --workspace-id "00bcfcd2-97d8-48b0-8ae4-67e7395ac373" \
    --lakehouse-name "ConferenceDataLakehouse" \
    --report-file "powerbi-templates/Conference-Attendance-Report.pbix"
```

## 🎨 Visual Design Guidelines

### Color Scheme
- **Primary**: #3498DB (Blue) - Professional, trustworthy
- **Success**: #27AE60 (Green) - Attended status, positive metrics
- **Warning**: #F39C12 (Orange) - Ratings, attention items
- **Danger**: #E74C3C (Red) - No-shows, low ratings
- **Neutral**: #95A5A6 (Gray) - Cancelled, inactive

### Typography
- **Titles**: 32px, Bold, #2C3E50
- **KPI Numbers**: 48px, Bold
- **Labels**: 12px, Regular
- **Table Text**: 10px, Regular

### Layout
- **Page Size**: 1280 x 720 (16:9 ratio)
- **Margins**: 20px all sides
- **Spacing**: 20px between visuals

## 📋 Report Filters (All Pages)

- **Date Range**: Session Date
- **Company**: Multi-select dropdown
- **Attendance Status**: Multi-select dropdown

## 🔄 Data Refresh

Configure automatic refresh:

1. **In Fabric workspace** → **Semantic Model Settings**
2. **Scheduled refresh** → **Configure**
3. **Frequency**: Daily at 6:00 AM
4. **Failure notifications**: Enable

## 📱 Mobile Layout (Optional)

Create optimized mobile view:
- Portrait orientation
- Stacked visuals
- Touch-friendly controls

## 🔗 Embed & Share

### Publish to Web
```powershell
# Get embed code
Publish-PowerBIToWeb -ReportId "<report-id>"
```

### Share Link
```
https://app.powerbi.com/groups/00bcfcd2-97d8-48b0-8ae4-67e7395ac373/reports/<report-id>
```

## 🎯 Use Cases

- **Event Organizers**: Track real-time attendance
- **Marketing Teams**: Analyze registration trends
- **Session Hosts**: Review feedback and ratings
- **Management**: Executive dashboard for event ROI

## 🔧 Customization

To modify the template:

1. Edit `powerbi-templates/attendance-report-template.json`
2. Add/remove visuals in the `pages` array
3. Update measures in the `measures` array
4. Re-deploy using the automated script

## 📊 Sample Insights

With this report, you can answer:

- ✅ What's our overall attendance rate?
- ✅ Which sessions are most popular?
- ✅ Which companies send the most attendees?
- ✅ What's the average satisfaction rating?
- ✅ Who are the no-shows?
- ✅ What time do most people check in?

## 🚀 Next Steps

1. **Deploy** the report using automated script
2. **Customize** visuals to match your branding
3. **Schedule** daily data refresh
4. **Share** with stakeholders
5. **Monitor** attendance metrics in real-time

---

**Full automation achieved!** 🎉

Deploy everything with one command, from Azure infrastructure to Power BI reports!
