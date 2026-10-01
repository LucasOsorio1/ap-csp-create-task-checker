import java.util.ArrayList;
import java.util.Scanner;

public class GradeBook {
    public static double average(ArrayList<Integer> grades) {
        int total = 0;
        for (int g : grades) {
            total += g;
        }
        return (double) total / grades.size();
    }

    public static void main(String[] args) {
        Scanner in = new Scanner(System.in);
        ArrayList<Integer> grades = new ArrayList<Integer>();
        System.out.print("How many grades? ");
        int n = in.nextInt();
        for (int i = 0; i < n; i++) {
            grades.add(in.nextInt());
        }
        double avg = average(grades);
        if (avg >= 90) {
            System.out.println("A average: " + avg);
        } else {
            System.out.println("Average: " + avg);
        }
    }
}
