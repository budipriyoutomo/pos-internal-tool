# core/report_generator.py
import datetime
from pathlib import Path
from config.settings import settings

class ReportGenerator:
    def __init__(self):
        self.reports_dir = settings.REPORTS_DIR
    
    def generate(self, outlet, currentdate, transactions, dine_in, takeaway):
        """
        Generate report dengan format original
        
        Args:
            outlet: Outlet code
            currentdate: Date string (YYYY-MM-DD)
            transactions: List of transaction summaries (bsum_trans)
            dine_in: List of dine-in items (bsum_menu with salemode=1)
            takeaway: List of takeaway items (bsum_menu with salemode=2)
        """
        # Parse transaction data (bsum_trans)
        disc = 0
        trans = 0
        service = 0
        tax = 0
        summary = ""
        outletcode = outlet
        outletname = outlet
        
        if transactions and len(transactions) > 0:
            x = transactions[-1]  # ambil data terakhir
            summary = str(x[0]) if len(x) > 0 else ""
            disc = int(x[1]) if len(x) > 1 else 0
            trans = x[2] if len(x) > 2 else 0
            service = int(x[3]) if len(x) > 3 else 0
            tax = int(x[4]) if len(x) > 4 else 0
            outletcode = str(x[6]) if len(x) > 6 else outlet
            outletname = str(x[7]) if len(x) > 7 else outlet
        
        # Create filename
        filename = self.reports_dir / f"{outlet}_{currentdate}.txt"
        
        # Generate report dengan format original
        with open(filename, 'w', encoding='utf-8') as f:
            # Header
            f.write("Consolidate Sale".center(35))
            
            currentdate_head = datetime.datetime.strptime(currentdate, '%Y-%m-%d').strftime('%d %B %Y')
            endtime = "End Time " + datetime.datetime.now().strftime('%H:%M:%S')
            
            f.write("\n" + currentdate_head.center(35) + "\n")
            f.write(endtime.center(35) + "\n")
            f.write(("Shop:" + outletname).center(35))
            f.write("\n" + outletcode + ":" + outletname)
            
            # Dine In section
            f.write("\nDine In\n")
            totaldine = 0
            countdine = 0
            
            for y in dine_in:
                a = str(y[0])[0:14] if y and len(y) > 0 else ""
                b = str(int(y[1])) if len(y) > 1 else "0"
                c = str(int(y[2])) if len(y) > 2 else "0"
                
                totaldine += int(c)
                countdine += int(b)
                
                d = a.ljust(15) + b.center(10) + c.rjust(10) + " \n"
                f.write(d)
            
            f.write("Sub Total " + str(int(totaldine)).rjust(25))
            f.write("\nDiscount" + str(disc).rjust(27))
            f.write("\nTotal Dine In :" + str(int(countdine)).center(10) + str(int(totaldine - disc)).rjust(10))
            
            # Take Away section
            f.write("\n\nTake Away \n")
            totaltake = 0
            counttake = 0
            
            for z in takeaway:
                a = str(z[0]) if z and len(z) > 0 else ""
                b = str(int(z[1])) if len(z) > 1 else "0"
                c = str(int(z[2])) if len(z) > 2 else "0"
                
                totaltake += int(c)
                counttake += int(b)
                
                d = a.ljust(15) + b.center(10) + c.rjust(10) + " \n"
                f.write(d)
            
            f.write("Total Take Away : " + str(int(counttake)).center(3) + str(int(totaltake)).rjust(14))
            
            # Summary
            f.write("\n\nSub Total " + str(int((totaldine + totaltake))).rjust(25))
            f.write("\nDiscount" + str(int(disc)).rjust(27))
            
            # Perbaikan perhitungan sub total (sesuai original)
            total_all = totaldine + totaltake
            f.write("\nSub Total : " + str(int((countdine + counttake))).center(15) + str(int(total_all - disc)).rjust(8))
            
            # Footer
            f.write("\n\n" + outletcode + ":" + str(outletname[0:18]) + summary.rjust(13))
            f.write("\nDiscount".ljust(25) + str(disc).rjust(11))
            f.write("\nSub Total".ljust(25) + str(trans).rjust(11))
            f.write("\nSVC".ljust(25) + str(service).rjust(11))
            f.write("\nPb1".ljust(25) + str(tax).rjust(11))
            f.write("\n\nTotal Sales" + str(int(trans + service + tax)).rjust(24))
        
        return str(filename)