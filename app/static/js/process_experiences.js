const getCurrentDate = () => {
   const now = new Date();
   return {
      day: now.getDate(),
      month: now.getMonth() + 1,  // JavaScript months are 0-indexed
      year: now.getFullYear()
   };
};

const calculateDuration = (start, end) => {
   const startDate = new Date(start.year, start.month - 1, start.day);
   const endDate = end || getCurrentDate();

   const diffTime = Math.abs(new Date(endDate.year, endDate.month - 1, endDate.day) - startDate);
   const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

   return {
      years: Math.floor(diffDays / 365),
      months: Math.floor((diffDays % 365) / 30),
      days: diffDays % 30
   };
};

const filterExperiences = (experiences, company_name, job_title) => {
   const currentDate = getCurrentDate();

   const filteredExperiences = experiences.filter(exp => {
      if (exp.ends_at !== null) return false; // Only consider ongoing experiences

      const duration = calculateDuration(exp.starts_at, currentDate);

      const isRecentRoleMatch = exp.title === job_title && duration.years === 0 && duration.months < 6;
      const isLongTermCompanyMatch = exp.company === company_name && duration.years >= 10;

      return isRecentRoleMatch || isLongTermCompanyMatch;
   });

   // Remove duplicates (if any)
   const uniqueExperiences = filteredExperiences.filter((exp, index, self) =>
      index === self.findIndex((t) => t.company === exp.company && t.title === exp.title)
   );

   return uniqueExperiences.map(exp => ({
      company: exp.company,
      title: exp.title,
      duration: `${calculateDuration(exp.starts_at, currentDate).years} years, ${calculateDuration(exp.starts_at, currentDate).months} months`
   }));
};