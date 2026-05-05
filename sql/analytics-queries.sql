-- Conference Attendance Analytics Queries
-- Run these queries in your Fabric Lakehouse after data is loaded

-- =============================================================================
-- ATTENDANCE OVERVIEW
-- =============================================================================

-- Total registrations and attendance summary
SELECT 
    COUNT(*) as TotalRegistrations,
    SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) as TotalAttended,
    SUM(CASE WHEN AttendanceStatus = 'Registered' THEN 1 ELSE 0 END) as StillRegistered,
    SUM(CASE WHEN AttendanceStatus = 'No-show' THEN 1 ELSE 0 END) as NoShows,
    SUM(CASE WHEN AttendanceStatus = 'Cancelled' THEN 1 ELSE 0 END) as Cancelled,
    ROUND(100.0 * SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) / COUNT(*), 2) as AttendanceRate
FROM conference_attendance;

-- =============================================================================
-- SESSION ANALYSIS
-- =============================================================================

-- Session attendance and ratings
SELECT 
    SessionName,
    SessionDate,
    SessionTime,
    COUNT(*) as TotalRegistrations,
    SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) as ActualAttendees,
    SUM(CASE WHEN AttendanceStatus = 'No-show' THEN 1 ELSE 0 END) as NoShows,
    ROUND(100.0 * SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) / COUNT(*), 2) as AttendanceRate,
    AVG(CAST(SessionRating as FLOAT)) as AverageRating,
    COUNT(SessionRating) as NumberOfRatings
FROM conference_attendance
GROUP BY SessionName, SessionDate, SessionTime
ORDER BY AverageRating DESC;

-- Top rated sessions
SELECT 
    SessionName,
    AVG(CAST(SessionRating as FLOAT)) as AverageRating,
    COUNT(SessionRating) as RatingCount,
    MAX(SessionRating) as HighestRating,
    MIN(SessionRating) as LowestRating
FROM conference_attendance
WHERE SessionRating IS NOT NULL
GROUP BY SessionName
HAVING COUNT(SessionRating) >= 3  -- At least 3 ratings
ORDER BY AverageRating DESC, RatingCount DESC;

-- Sessions with low attendance
SELECT 
    SessionName,
    COUNT(*) as Registered,
    SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) as Attended,
    SUM(CASE WHEN AttendanceStatus = 'No-show' THEN 1 ELSE 0 END) as NoShows,
    ROUND(100.0 * SUM(CASE WHEN AttendanceStatus = 'No-show' THEN 1 ELSE 0 END) / COUNT(*), 2) as NoShowRate
FROM conference_attendance
GROUP BY SessionName
HAVING COUNT(*) > 0
ORDER BY NoShowRate DESC;

-- =============================================================================
-- COMPANY AND ATTENDEE ANALYSIS
-- =============================================================================

-- Company participation
SELECT 
    Company,
    COUNT(DISTINCT CONCAT(FirstName, ' ', LastName)) as UniqueAttendees,
    COUNT(*) as TotalRegistrations,
    SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) as SessionsAttended,
    ROUND(AVG(CAST(SessionRating as FLOAT)), 2) as AvgRatingGiven
FROM conference_attendance
GROUP BY Company
ORDER BY TotalRegistrations DESC;

-- Job title distribution
SELECT 
    JobTitle,
    COUNT(DISTINCT CONCAT(FirstName, ' ', LastName)) as NumberOfAttendees,
    AVG(CAST(SessionRating as FLOAT)) as AverageRating
FROM conference_attendance
GROUP BY JobTitle
ORDER BY NumberOfAttendees DESC;

-- Most engaged attendees (highest number of sessions)
SELECT 
    FirstName,
    LastName,
    Email,
    Company,
    JobTitle,
    COUNT(*) as SessionsRegistered,
    SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) as SessionsAttended,
    ROUND(AVG(CAST(SessionRating as FLOAT)), 2) as AverageRating
FROM conference_attendance
GROUP BY FirstName, LastName, Email, Company, JobTitle
ORDER BY SessionsAttended DESC, SessionsRegistered DESC;

-- =============================================================================
-- TIME-BASED ANALYSIS
-- =============================================================================

-- Registration timeline
SELECT 
    RegistrationDate,
    COUNT(*) as RegistrationsOnDate,
    SUM(COUNT(*)) OVER (ORDER BY RegistrationDate) as CumulativeRegistrations
FROM conference_attendance
GROUP BY RegistrationDate
ORDER BY RegistrationDate;

-- Session schedule overview
SELECT 
    SessionDate,
    COUNT(DISTINCT SessionName) as NumberOfSessions,
    COUNT(*) as TotalRegistrations,
    SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) as TotalAttendees
FROM conference_attendance
GROUP BY SessionDate
ORDER BY SessionDate;

-- =============================================================================
-- FEEDBACK ANALYSIS
-- =============================================================================

-- Sessions with feedback comments
SELECT 
    SessionName,
    FirstName,
    LastName,
    Company,
    SessionRating,
    FeedbackComments
FROM conference_attendance
WHERE FeedbackComments IS NOT NULL AND FeedbackComments != ''
ORDER BY SessionRating DESC, SessionName;

-- Rating distribution
SELECT 
    SessionRating,
    COUNT(*) as NumberOfRatings,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as Percentage
FROM conference_attendance
WHERE SessionRating IS NOT NULL
GROUP BY SessionRating
ORDER BY SessionRating DESC;

-- =============================================================================
-- DATA QUALITY CHECKS
-- =============================================================================

-- Check for duplicate registrations
SELECT 
    Email,
    SessionName,
    COUNT(*) as DuplicateCount
FROM conference_attendance
GROUP BY Email, SessionName
HAVING COUNT(*) > 1;

-- Records with missing data
SELECT 
    'Missing CheckInTime' as Issue,
    COUNT(*) as RecordCount
FROM conference_attendance
WHERE AttendanceStatus = 'Attended' AND (CheckInTime IS NULL OR CheckInTime = '')
UNION ALL
SELECT 
    'Missing Rating' as Issue,
    COUNT(*) as RecordCount
FROM conference_attendance
WHERE AttendanceStatus = 'Attended' AND SessionRating IS NULL
UNION ALL
SELECT 
    'Missing Email' as Issue,
    COUNT(*) as RecordCount
FROM conference_attendance
WHERE Email IS NULL OR Email = '';

-- =============================================================================
-- EXPORT VIEWS (Create these as views for Power BI)
-- =============================================================================

-- Session summary view
CREATE OR REPLACE VIEW vw_session_summary AS
SELECT 
    SessionName,
    SessionDate,
    SessionTime,
    COUNT(*) as TotalRegistrations,
    SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) as Attended,
    SUM(CASE WHEN AttendanceStatus = 'No-show' THEN 1 ELSE 0 END) as NoShows,
    ROUND(100.0 * SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) / COUNT(*), 2) as AttendanceRate,
    AVG(CAST(SessionRating as FLOAT)) as AverageRating,
    COUNT(SessionRating) as RatingCount
FROM conference_attendance
GROUP BY SessionName, SessionDate, SessionTime;

-- Attendee engagement view
CREATE OR REPLACE VIEW vw_attendee_engagement AS
SELECT 
    Email,
    FirstName,
    LastName,
    Company,
    JobTitle,
    COUNT(*) as SessionsRegistered,
    SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) as SessionsAttended,
    ROUND(100.0 * SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) / COUNT(*), 2) as AttendanceRate,
    AVG(CAST(SessionRating as FLOAT)) as AverageRating
FROM conference_attendance
GROUP BY Email, FirstName, LastName, Company, JobTitle;

-- Company participation view
CREATE OR REPLACE VIEW vw_company_participation AS
SELECT 
    Company,
    COUNT(DISTINCT Email) as UniqueAttendees,
    COUNT(*) as TotalRegistrations,
    SUM(CASE WHEN AttendanceStatus = 'Attended' THEN 1 ELSE 0 END) as SessionsAttended,
    ROUND(AVG(CAST(SessionRating as FLOAT)), 2) as AverageRating
FROM conference_attendance
GROUP BY Company;
