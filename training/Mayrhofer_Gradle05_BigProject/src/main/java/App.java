import org.opencv.core.CvType;
import org.opencv.core.Mat;

/*
 * This Java source file was generated by the Gradle 'init' task.
 */
public class App {
    public String getGreeting() {
        return "Hello world.";
    }

    public static void main(String[] args) {
        System.out.println(new App().getGreeting());

        Mat mat = Mat.eye(3, 3, CvType.CV_8UC1);
        System.out.println("mat = "+mat.dump());
    }
}
