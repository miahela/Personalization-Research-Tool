document.addEventListener("alpine:init", () => {
   // noinspection JSUnresolvedReference
   Alpine.data("sheetProcessor", () => ({
      selectedSheetIds: [],
      entries: [],
      currentEntryIndex: 0,
      isLoading: false,
      isSaving: false,
      btw: "By the way, ",
      _totalCount: -1,
      eventSource: null,
      sheets: window.initialSheets || [], // Use the global variable
      awaitingUserAction: false,
      processingPaused: false,

      get totalCount() {
         if (this._totalCount === -1) this._totalCount = this.sheets.filter(sheet => this.selectedSheetIds.includes(sheet.id)).reduce((total, sheet) => total + sheet.empty_by_the_way_count, 0);
         return this._totalCount;
      },

      processSelectedSheets() {
         if (this.selectedSheetIds.length === 0) return;

         this.reset();
         this.isLoading = true;

         if (this.eventSource) {
            this.eventSource.close();
         }

         const queryParams = this.selectedSheetIds.map(id => `sheet_id=${encodeURIComponent(id)}`).join("&");
         const url = `/process_stream?${queryParams}&small_batch_size=2&large_batch_size=10`;

         this.eventSource = new EventSource(url);

         this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.complete) {
               console.log("Processing complete");
               this.eventSource.close();
               this.isLoading = false;
               return;
            }

            if (data.waiting_for_user_action) {
               this.awaitingUserAction = true;
               console.log("Awaiting user action");
               // Don't automatically continue, wait for user input
               return;
            }

            if (data.await_user_action) {
               this.processingPaused = true;
               console.log("Processing paused. Waiting for user action.");
               return;
            }

            if (data.contacts) {
               this.entries = this.entries.concat(data.contacts);
               this.updateEditableFields();
            }

            this.$nextTick(() => {
               // Any UI updates after processing contacts
            });
         };

         this.eventSource.onerror = (error) => {
            console.error("EventSource failed:", error);
            this.eventSource.close();
            this.isLoading = false;
         };
      },

      async continueProcessing() {
         if (this.processingPaused) {
            try {
               const response = await fetch("/continue_processing", {
                  method: "POST",
                  headers: {
                     "Content-Type": "application/json"
                  }
               });
               const result = await response.json();
               console.log("Continue processing result:", result);
               this.processingPaused = false;
            } catch (error) {
               console.error("Error continuing processing:", error);
            }
         }
      },

      updateEditableFields() {
         this.currentEntry.editableFields = this.currentEntry["colored_cells"].map(cellName => ({
            name: cellName,
            value: this.currentEntry[cellName] || ""
         }));

         if (this.currentEntry.relevant_experiences && this.currentEntry.relevant_experiences.title_mismatch) {
            this.currentEntry.editableFields.push({
               name: "Corrected Job Title",
               value: this.currentEntry.relevant_experiences.most_likely_current_title
            });
         }
      },

      reset() {
         this.entries = [];
         this.currentEntryIndex = 0;
         this.isLoading = false;
         this.btw = "By the way, ";
         this.processedCount = 0;
         this._totalCount = -1;
         if (this.eventSource) {
            this.eventSource.close();
         }

      },

      get currentEntry() {
         return this.entries[this.currentEntryIndex] || null;
      },

      get currentEntryToJSON() {
         return JSON.stringify(this.currentEntry, null, 2);
      },

      async saveEntry() {
         this.isSaving = true;
         const entryData = {};
         for (let field of this.currentEntry.editableFields) {
            entryData[field.name] = field.value;
         }

         entryData["Personalization Date"] = new Date().toLocaleDateString();
         entryData["by the way"] = this.btw;

         const body = {
            sheet_id: this.currentEntry["spreadsheet_id"],
            entry_data: entryData,
            row_number: this.currentEntry.row_number + 1,
            username: this.currentEntry["linkedin_username"]
         };
         try {
            const response = await fetch("/save", {
               method: "POST",
               headers: {
                  "Content-Type": "application/json"
               },
               body: JSON.stringify(body)
            });
            await this.nextEntry();
         } catch (error) {
            console.error("Error saving entry:", error);
         } finally {
            this.isSaving = false;
         }
      },

      async checkAndContinueProcessing() {
         const remainingEntries = this.entries.length - this.currentEntryIndex;
         const thresholdForContinue = 4; // Adjust this value as needed

         if (remainingEntries <= thresholdForContinue && this.processingPaused) {
            console.log(`Only ${remainingEntries} entries left. Continuing processing...`);
            await this.continueProcessing();
         }
      },

      async nextEntry() {
         this.btw = "By the way, ";
         this.currentEntryIndex += 1;
         this.updateEditableFields();
         await this.checkAndContinueProcessing();
      },

      get contactTitle() {
         return `${this.currentEntry.contact_first_name} ${this.currentEntry.contact_last_name}`;
      },

      calculateDuration(startDate, endDate) {
         const start = new Date(startDate.year, startDate.month - 1, startDate.day);
         const end = endDate ? new Date(endDate.year, endDate.month - 1, endDate.day) : new Date();
         const diffTime = Math.abs(end - start);
         const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
         const years = Math.floor(diffDays / 365);
         const months = Math.floor((diffDays % 365) / 30);
         return `${years} yr${years !== 1 ? 's' : ''} ${months} mo${months !== 1 ? 's' : ''}`;
      },

      formatDate(date) {
         if (!date) return '';
         const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
         return `${months[date.month - 1]} ${date.year}`;
      },

      formatExperience(exp) {
         return {
            ...exp,
            duration: this.calculateDuration(exp.starts_at, exp.ends_at),
            isCurrent: !exp.ends_at,
            formattedStartDate: this.formatDate(exp.starts_at),
            formattedEndDate: this.formatDate(exp.ends_at),
            employmentType: exp.employment_type || 'Full-time', // Assuming a default if not provided
            location: exp.location || 'Location not specified'
         };
      },

      get relevantExperiences() {
         if (!this.currentEntry || !this.currentEntry.relevant_experiences) {
            return [];
         }

         return this.currentEntry.relevant_experiences.experiences.map(exp => this.formatExperience(exp));
      },

      get campaignInstance() {
         const hookParts = this.currentEntry.hook_name.split(" - ");
         const hookName = hookParts.length > 1 ? hookParts.slice(0, 2).join(" - ") : this.currentEntry.hook_name;
         return `${hookName} : ${this.currentEntry.messenger_campaign_instance}`;
      },

      get bio() {
         return this.currentEntry?.bio || "";
      },

      get company() {
         return this.currentEntry?.contact_company_name || "";
      },

      get industry() {
         return this.currentEntry?.industry || "";
      },

      get languages() {
         return this.currentEntry?.languages || [];
      },

      // Card-related computed properties
      get profilePicture() {
         return this.currentEntry?.profile_picture || null;
      },

      get initials() {
         return this.currentEntry ? `${this.currentEntry.contact_first_name[0]}${this.currentEntry.contact_last_name[0]}` : "";
      },

      get companyWebsite() {
         return this.currentEntry?.company?.website || null;
      },

      get interviewsAndPodcasts() {
         return this.currentEntry?.interviews_and_podcasts || [];
      },

      get volunteerWork() {
         return this.currentEntry?.volunteer_work || [];
      },

      get companyAboutLink() {
         return this.currentEntry?.company?.about_links || null;
      },

      get btwLanguageHint() {
         return this.currentEntry?.languages?.length >= 2 ? `What’s the secret to learning ${this.currentEntry.languages.length} languages?` : "";
      },

      get caseStudyLinks() {
         return this.currentEntry?.company?.case_study_links || null;
      },

      // Card-related methods
      renderListItems(items) {
         if (!items) return "";
         return items.map(item => this.renderListItem(item)).join("");
      },

      renderListItem(item) {
         if (!item) return "";
         const content = this.getItemContent(item);
         const sublist = this.getSublist(item);
         const sublistHtml = this.renderSublist(sublist);

         return `<li>${content}${sublistHtml}</li>`;
      },

      getItemContent(item) {
         return item.url ?
            `<p class="truncate"><a href="${item.url}" class="link link-primary" target="_blank">${item.title || item.url}</a></p>` :
            `<span>${item.title || item.text}</span>`;
      },

      renderSublist(sublist) {
         if (!sublist.length) return "";
         return `
            <ul class="list-disc list-outside ml-5 text-neutral-600 text-sm">
                ${sublist.map(subItem => `<li><span class="font-bold text-sm text-neutral-400">${subItem.label}</span> ${subItem.value}</li>`).join("")}
            </ul>
         `;
      },

      getSublist(item) {
         const sublist = [];
         if (item.title && !item.cause) sublist.push({
            label: "Title:",
            value: item.title
         });
         if (item.description) sublist.push({
            label: "Description:",
            value: item.description
         });
         if (item.date) sublist.push({
            label: "Date:",
            value: item.date
         });
         if (item.cause) sublist.push({
            label: "Cause:",
            value: item.cause
         });
         if (item.company) sublist.push({
            label: "Company:",
            value: item.company
         });
         return sublist;
      }
   }));

   Alpine.data("complexList", (initialItems, showTitleInSublist = true) => ({
      items: initialItems,
      showTitleInSublist,

      updateItems(newItems) {
         this.items = [...newItems]; // Create a new array to trigger reactivity
      },

      getItemContent(item) {
         if (!item) return "";
         return item.url ? {
            type: "link",
            url: item.url,
            text: item.title || item.url
         } : {
            type: "text",
            text: item.title || item.text
         };
      },

      getSublist(item) {
         if (!item) return [];
         return [
            this.showTitleInSublist && {
               label: "Title",
               value: item.title
            },
            {
               label: "Cause",
               value: item.cause
            },
            {
               label: "Description",
               value: item.description
            },
            {
               label: "Date",
               value: item.date
            },
            {
               label: "Company",
               value: item.company
            }
         ].filter(subItem => subItem.value);
      }
   }));
});