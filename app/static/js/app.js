document.addEventListener("alpine:init", () => {
   // noinspection JSUnresolvedReference
   Alpine.data("sheetProcessor", () => ({
      selectedSheetId: "",
      entries: [],
      currentEntryIndex: 0,
      isLoading: false,
      btw: "By the way, ",
      jobTitlePlural: "",
      editableFields: [],
      coloredCells: [],

      async processSheet() {
         if (!this.selectedSheetId) return;
         this.reset();
         this.isLoading = true;
         try {
            const response = await fetch("/process", {
               method: "POST",
               headers: {
                  "Content-Type": "application/json"
               },
               body: JSON.stringify({
                  sheet_id: this.selectedSheetId
               })
            });
            const data = await response.json();

            this.entries = data.new_connections;
            this.currentEntryIndex = 0;

            this.coloredCells = data.colored_cells;
            for (let i = 0; i < this.coloredCells.length; i++) {
               this.editableFields.push({
                  name: this.coloredCells[i],
                  value: this.currentEntry[this.coloredCells[i]] || ""
               });
            }
         } catch (error) {
            console.error("Error processing sheet:", error);
         } finally {
            this.isLoading = false;
         }
      },

      reset() {
         this.entries = [];
         this.currentEntryIndex = 0;
         this.isLoading = false;
         this.btw = "By the way, ";
         this.jobTitlePlural = "";
         this.editableFields = [];
         this.coloredCells = [];
      },

      get currentEntry() {
         return this.entries[this.currentEntryIndex] || null;
      },

      async saveEntry() {
         this.isLoading = true;
         const entryData = {};
         for (let i = 0; i < this.editableFields.length; i++) {
            entryData[this.editableFields[i].name] = this.editableFields[i].value;
         }

         entryData["Personalization Date"] = new Date().toLocaleDateString();
         entryData["by the way"] = this.btw;

         const body = {
            sheet_id: this.selectedSheetId,
            entry_data: entryData,
            row_number: this.currentEntry.row_number + 1,
            username: this.currentEntry['linkedin_username']
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
            this.isLoading = false;
         }
      },

      async nextEntry() {
         this.btw = "By the way, ";
         this.currentEntryIndex += 1;
         for (let i = 0; i < this.coloredCells.length; i++) {
            this.editableFields[i].value = this.currentEntry[this.coloredCells[i]] || "";
         }
      },

      get contactTitle() {
         return `${this.currentEntry.contact_first_name} ${this.currentEntry.contact_last_name}`;
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

      // Card-related computed properties
      get profilePicture() {
         return this.currentEntry?.profile_picture || null;
      },

      get initials() {
         return this.currentEntry ? `${this.currentEntry.contact_first_name[0]}${this.currentEntry.contact_last_name[0]}` : "";
      },

      get companyWebsite() {
         return this.currentEntry?.company_website || null;
      },

      get interviewsAndPodcasts() {
         return this.currentEntry?.interviews_and_podcasts || [];
      },

      get volunteerWork() {
         return this.currentEntry?.volunteer_work || [];
      },

      get companyAboutLink() {
         return this.currentEntry?.company_about_link || null;
      },

      get btwLanguageHint() {
         return this.currentEntry?.languages?.length >= 2 ? `What’s the secret to learning ${this.currentEntry.languages.length} languages?` : "";
      },

      get caseStudyLinks() {
         return this.currentEntry?.case_study_links || null;
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
         console.log("Updating items:", newItems);
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