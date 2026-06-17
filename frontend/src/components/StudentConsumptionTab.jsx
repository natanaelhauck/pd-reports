import { CourseHoursStudentDetails } from './CourseHoursStudentDetails.jsx';

export function StudentConsumptionTab({
  aluno,
  apiBaseUrl,
  authHeaders,
  onBackToList,
  showBackToList,
}) {
  return (
    <CourseHoursStudentDetails
      aluno={aluno}
      apiBaseUrl={apiBaseUrl}
      authHeaders={authHeaders}
      onBack={showBackToList ? onBackToList : undefined}
    />
  );
}
