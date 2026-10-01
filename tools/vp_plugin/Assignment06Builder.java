import com.vp.plugin.*;
import com.vp.plugin.diagram.*;
import com.vp.plugin.diagram.shape.*;
import com.vp.plugin.model.*;
import com.vp.plugin.model.factory.IModelElementFactory;
import java.awt.*;
import java.io.File;
import java.util.*;

/** Editable Visual Paradigm UML for the multimodal search assignment. */
public final class Assignment06Builder implements VPPlugin, VPPluginCommandLineSupport {
    private final DiagramManager dm = ApplicationManager.instance().getDiagramManager();
    private final IModelElementFactory factory = IModelElementFactory.instance();
    private final File root = new File(System.getProperty("ptit.assignment.root"));
    private IActor customerActor;
    private Map<String,IClass> architectureClasses;
    private Map<String,IShapeUIModel> architectureViews;

    @Override public void loaded(VPPluginInfo info) { }
    @Override public void unloaded() { }

    private void style(IShapeUIModel shape, int x, int y, int w, int h, Color fill) {
        shape.setBounds(x, y, w, h);
        shape.setBackground(fill);
        shape.getFillColor().setColor1(fill, true);
        shape.setForeground(new Color(36, 53, 71));
        shape.getElementFont().setValues("Arial", Font.PLAIN, 16, new Color(28, 42, 57));
        shape.setRequestResetCaption(true);
    }

    private void export(IDiagramUIModel diagram, String stem) throws Exception {
        File dir = new File(root, "diagrams");
        dir.mkdirs();
        ExportDiagramAsImageOption png = new ExportDiagramAsImageOption(ModelConvertionManager.IMAGE_TYPE_PNG);
        png.setScale(1.6f);
        ApplicationManager.instance().getModelConvertionManager().exportDiagramAsImage(
            diagram, new File(dir, stem + ".png"), png, (Rectangle) null);
        ApplicationManager.instance().getModelConvertionManager().exportDiagramAsImage(
            diagram, new File(dir, stem + ".svg"), ModelConvertionManager.IMAGE_TYPE_SVG);
    }

    private IShapeUIModel useCase(IUseCaseDiagramUIModel diagram, ISystem system, IShapeUIModel boundary,
                                   String name, int x, int y, Map<String,IUseCase> models,
                                   Map<String,IShapeUIModel> views) {
        IUseCase model = factory.createUseCase();
        model.setName(name);
        system.addChild(model);
        IShapeUIModel view = (IShapeUIModel) dm.createDiagramElement(diagram, model);
        style(view, x, y, 230, 65, new Color(224, 241, 255));
        boundary.addChild(view);
        models.put(name, model); views.put(name, view);
        return view;
    }

    private void association(IDiagramUIModel diagram, IModelElement from, IModelElement to,
                             IShapeUIModel fromView, IShapeUIModel toView) {
        IAssociation relation = factory.createAssociation();
        relation.setFrom(from); relation.setTo(to);
        dm.createConnector(diagram, relation, fromView, toView, null);
    }

    private void routedAssociation(IDiagramUIModel diagram, IModelElement from, IModelElement to,
                                   IShapeUIModel fromView, IShapeUIModel toView, Point[] points) {
        IAssociation relation = factory.createAssociation();
        relation.setFrom(from); relation.setTo(to);
        dm.createConnector(diagram, relation, fromView, toView, points);
    }

    private void generalization(IDiagramUIModel diagram, IModelElement parent, IModelElement child,
                                IShapeUIModel parentView, IShapeUIModel childView) {
        // VP's API stores the parent in from, child in to; its UML arrow points to parent.
        IGeneralization relation = factory.createGeneralization();
        relation.setFrom(parent); relation.setTo(child);
        dm.createConnector(diagram, relation, parentView, childView, null);
    }

    private void useCaseDiagram() throws Exception {
        IUseCaseDiagramUIModel diagram = (IUseCaseDiagramUIModel) dm.createDiagram(
            IDiagramTypeConstants.DIAGRAM_TYPE_USE_CASE_DIAGRAM);
        diagram.setName("01 - Use Case - Multimodal Search");
        diagram.setDiagramBackground(Color.WHITE);
        ISystem system = factory.createSystem();
        system.setName("E-Commerce Multimodal Search System");
        IShapeUIModel boundary = (IShapeUIModel) dm.createDiagramElement(diagram, system);
        style(boundary, 290, 30, 900, 540, Color.WHITE);
        customerActor = factory.createActor(); customerActor.setName("Customer");
        IShapeUIModel actorTop = (IShapeUIModel) dm.createDiagramElement(diagram, customerActor);
        style(actorTop, 110, 300, 45, 80, Color.WHITE);
        actorTop.getCaptionUIModel().setBounds(70,385,135,25);
        Map<String,IUseCase> models = new LinkedHashMap<>();
        Map<String,IShapeUIModel> views = new LinkedHashMap<>();
        useCase(diagram,system,boundary,"Search Product",600,70,models,views);
        useCase(diagram,system,boundary,"Search by Keyword",350,215,models,views);
        useCase(diagram,system,boundary,"Search by Voice",620,215,models,views);
        useCase(diagram,system,boundary,"Search by Image",890,215,models,views);
        useCase(diagram,system,boundary,"Search Order",350,400,models,views);
        useCase(diagram,system,boundary,"View Product",620,400,models,views);
        useCase(diagram,system,boundary,"View Order",890,400,models,views);
        routedAssociation(diagram,customerActor,models.get("Search Product"),actorTop,views.get("Search Product"),
            new Point[]{new Point(155,315),new Point(205,315),new Point(205,102),new Point(600,102)});
        routedAssociation(diagram,customerActor,models.get("Search Order"),actorTop,views.get("Search Order"),
            new Point[]{new Point(155,330),new Point(220,330),new Point(220,432),new Point(350,432)});
        routedAssociation(diagram,customerActor,models.get("View Product"),actorTop,views.get("View Product"),
            new Point[]{new Point(155,350),new Point(240,350),new Point(240,480),new Point(620,480),new Point(620,432)});
        routedAssociation(diagram,customerActor,models.get("View Order"),actorTop,views.get("View Order"),
            new Point[]{new Point(155,370),new Point(260,370),new Point(260,500),new Point(890,500),new Point(890,432)});
        for (String name : new String[]{"Search by Keyword","Search by Voice","Search by Image"})
            generalization(diagram,models.get("Search Product"),models.get(name),
                views.get("Search Product"),views.get(name));
        export(diagram,"01_use_case");
    }

    private IClass architectureClass(IClassDiagramUIModel diagram, IPackage group,
                                     IShapeUIModel groupView, String name,
                                     int x, int y, int w, int h,
                                     String[][] attributes, String[][] operations) {
        IClass model = factory.createClass();
        model.setName(name);
        group.addChild(model);
        for (String[] field : attributes) {
            IAttribute attribute = factory.createAttribute();
            attribute.setName(field[0]);
            attribute.setType(field[1]);
            attribute.setVisibility("private");
            model.addAttribute(attribute);
        }
        for (String[] signature : operations) {
            IOperation operation = factory.createOperation();
            operation.setName(signature[0]);
            operation.setReturnType(signature[1]);
            for (int i = 2; i < signature.length; i++) {
                String[] parts = signature[i].split(":", 2);
                IParameter parameter = factory.createParameter();
                parameter.setName(parts[0]);
                if (parts.length > 1) parameter.setType(parts[1]);
                operation.addParameter(parameter);
            }
            model.addOperation(operation);
        }
        IShapeUIModel view = (IShapeUIModel) dm.createDiagramElement(diagram,model);
        // Use VP's regular class box with its default name, attribute, and
        // operation compartments. White fill keeps the printed layer groups clear.
        view.setBounds(x,y,w,h);
        view.setBackground(Color.WHITE);
        view.getFillColor().setColor1(Color.WHITE,true);
        view.setRequestResetCaption(true);
        groupView.addChild(view);
        architectureClasses.put(name, model);
        architectureViews.put(name, view);
        return model;
    }

    private void classDependency(IDiagramUIModel diagram, String client, String supplier,
                                 Point start, Point end) {
        // UML dependency arrows point from the client class to the class it uses.
        IDependency relation = factory.createDependency();
        relation.setFrom(architectureClasses.get(client));
        relation.setTo(architectureClasses.get(supplier));
        dm.createConnector(diagram, relation, architectureViews.get(client), architectureViews.get(supplier),
            new Point[]{start, end});
    }

    private void architectureClassDiagram() throws Exception {
        IClassDiagramUIModel diagram = (IClassDiagramUIModel) dm.createDiagram(
            IDiagramTypeConstants.DIAGRAM_TYPE_CLASS_DIAGRAM);
        diagram.setName("02 - Class - Three-Layer Architecture");
        diagram.setDiagramBackground(Color.WHITE);
        architectureClasses = new LinkedHashMap<>();
        architectureViews = new LinkedHashMap<>();
        IPackage presentation = factory.createPackage();
        presentation.setName("Presentation Layer");
        IPackage application = factory.createPackage();
        application.setName("Application / Intelligence Layer");
        IPackage data = factory.createPackage();
        data.setName("Data Layer");
        IShapeUIModel p = (IShapeUIModel) dm.createDiagramElement(diagram,presentation);
        IShapeUIModel a = (IShapeUIModel) dm.createDiagramElement(diagram,application);
        IShapeUIModel d = (IShapeUIModel) dm.createDiagramElement(diagram,data);
        p.setBounds(30,30,400,590);
        a.setBounds(460,30,380,590);
        d.setBounds(870,30,365,590);
        for(IShapeUIModel layer : new IShapeUIModel[]{p,a,d}) {
            layer.setBackground(Color.WHITE);
            layer.getFillColor().setColor1(Color.WHITE,true);
            layer.setRequestResetCaption(true);
        }

        architectureClass(diagram,presentation,p,"VoiceInput",50,75,175,65,
            new String[][]{{"transcript","String"}},
            new String[][]{{"getTranscript","String"}});
        architectureClass(diagram,presentation,p,"ImageUpload",245,75,175,75,
            new String[][]{{"imagePath","String"}},
            new String[][]{{"selectImage","String"},{"validateImage","Boolean"}});
        architectureClass(diagram,presentation,p,"SearchUI",50,235,370,185,
            new String[][]{
                {"queryService","QueryService"},
                {"speechService","SpeechService"},
                {"imageService","ImageService"},
                {"searchService","SearchService"},
                {"orderService","OrderService"}
            },
            new String[][]{
                {"text","List<Product>","query:String"},
                {"voice","List<Product>","transcript:String"},
                {"image","List<Product>","path:String"},
                {"multimodal","List<Product>","text:String","image:String"},
                {"order","Order","customer:String","orderId:String"}
            });
        architectureClass(diagram,presentation,p,"SearchResultView",50,470,370,65,
            new String[][]{{"results","List<Product>"}},
            new String[][]{{"displayResults","void","items:List<Product>"}});

        architectureClass(diagram,application,a,"QueryService",485,70,330,85,
            new String[][]{{"colors","Set<String>"},{"brands","Set<String>"}},
            new String[][]{{"textQuery","Query","text:String"}});
        architectureClass(diagram,application,a,"SpeechService",485,160,330,65,
            new String[][]{{"mode","String"}},
            new String[][]{{"transcribe","String","transcript:String"}});
        architectureClass(diagram,application,a,"ImageService",485,235,330,65,
            new String[][]{{"whiteThreshold","Integer"}},
            new String[][]{{"validate","Path","imagePath:String"}});
        architectureClass(diagram,application,a,"SearchService",485,315,330,125,
            new String[][]{
                {"repository","ProductRepository"},
                {"vectorIndex","VectorIndex"},
                {"ranking","RankingService"}
            },
            new String[][]{
                {"queryMetadata","List<Map>"},
                {"search","List<Product>","query:Query","topK:Integer"},
                {"viewProduct","Product","productId:String"}
            });
        architectureClass(diagram,application,a,"RankingService",485,465,330,65,
            new String[][]{{"imageWeight","Float"}},
            new String[][]{{"rank","List<Product>","candidates:List<Product>"}});
        architectureClass(diagram,application,a,"OrderService",485,535,330,65,
            new String[][]{{"repository","OrderRepository"}},
            new String[][]{{"findOrder","Order","customerId:String","orderId:String"}});

        architectureClass(diagram,data,d,"ProductRepository",890,70,325,75,
            new String[][]{{"filePath","String"}},
            new String[][]{{"findAll","List<Product>"},{"get","Product","productId:String"}});
        architectureClass(diagram,data,d,"ProductDatabase",890,160,325,65,
            new String[][]{{"format","String"}},
            new String[][]{{"loadProducts","List<Product>"}});
        architectureClass(diagram,data,d,"VectorIndex",890,250,325,65,
            new String[][]{{"repository","ProductRepository"}},
            new String[][]{{"scores","Map<String,Float>","queryImage:String"}});
        architectureClass(diagram,data,d,"ImageStorage",890,340,325,65,
            new String[][]{{"rootPath","String"}},
            new String[][]{{"loadImage","Image","path:String"}});
        architectureClass(diagram,data,d,"OrderRepository",890,430,325,65,
            new String[][]{{"filePath","String"}},
            new String[][]{
                {"findOrder","Order","orderId:String","customerId:String"},
                {"latestOrder","Order","customerId:String"}
            });
        architectureClass(diagram,data,d,"OrderDatabase",890,520,325,65,
            new String[][]{{"format","String"}},
            new String[][]{{"loadOrders","List<Order>"}});

        // Model the actual class-level usage links. A package-only arrow would
        // leave the classes visually disconnected and hide which class calls which.
        classDependency(diagram,"VoiceInput","SearchUI",new Point(137,140),new Point(135,235));
        classDependency(diagram,"ImageUpload","SearchUI",new Point(332,150),new Point(335,235));
        classDependency(diagram,"SearchUI","SearchResultView",new Point(235,420),new Point(235,470));
        classDependency(diagram,"SearchUI","QueryService",new Point(420,260),new Point(485,102));
        classDependency(diagram,"SearchUI","SpeechService",new Point(420,282),new Point(485,192));
        classDependency(diagram,"SearchUI","ImageService",new Point(420,304),new Point(485,267));
        classDependency(diagram,"SearchUI","SearchService",new Point(420,326),new Point(485,377));
        classDependency(diagram,"SearchUI","OrderService",new Point(420,348),new Point(485,567));
        classDependency(diagram,"SearchService","RankingService",new Point(650,440),new Point(650,465));
        classDependency(diagram,"SearchService","ProductRepository",new Point(815,345),new Point(890,107));
        classDependency(diagram,"SearchService","VectorIndex",new Point(815,405),new Point(890,282));
        classDependency(diagram,"OrderService","OrderRepository",new Point(815,550),new Point(890,462));
        classDependency(diagram,"ProductRepository","ProductDatabase",new Point(1052,145),new Point(1052,160));
        classDependency(diagram,"VectorIndex","ImageStorage",new Point(1052,315),new Point(1052,340));
        classDependency(diagram,"OrderRepository","OrderDatabase",new Point(1052,495),new Point(1052,520));
        export(diagram,"02_three_layer_architecture");
    }

    private void message(IInteractionDiagramUIModel diagram, IModelElement from, IModelElement to,
                         IShapeUIModel fromView, IShapeUIModel toView,
                         String name, int x1, int x2, int y, boolean isReturn) {
        IMessage model = factory.createMessage(); model.setName(name);
        model.setFrom(from); model.setTo(to);
        if(isReturn) model.setActionType(factory.createActionTypeReturn());
        else { IActionTypeCall call = factory.createActionTypeCall(); call.setAsynchronous(false);
               model.setActionType(call); model.setAsynchronous(false); }
        Point[] points = {new Point(x1,y),new Point(x2,y)};
        IConnectorUIModel line = (IConnectorUIModel) dm.createConnector(diagram,model,fromView,toView,points);
        line.setRequestResetCaption(true);
    }

    private void activation(IInteractionDiagramUIModel diagram, IInteractionLifeLine lifeline,
                           int centerX, int startY, int endY) {
        IActivation model = factory.createActivation();
        lifeline.addActivation(model);
        IActivationUIModel shape = (IActivationUIModel) dm.createDiagramElement(diagram,model);
        shape.setBounds(centerX - IActivationUIModel.BODY_WIDTH / 2,startY,
            IActivationUIModel.BODY_WIDTH,endY - startY);
        Color fill = new Color(122,210,255);
        shape.setBackground(fill);
        shape.getFillColor().setColor1(fill,true);
        shape.setForeground(new Color(36,53,71));
    }

    private void sequenceDiagram() throws Exception {
        IInteractionDiagramUIModel diagram = (IInteractionDiagramUIModel) dm.createDiagram(
            IDiagramTypeConstants.DIAGRAM_TYPE_INTERACTION_DIAGRAM);
        diagram.setName("03 - Sequence - Voice Product Search");
        diagram.setDiagramBackground(Color.WHITE);
        diagram.setShowSequenceNumbers(true);
        diagram.setRequestRecalculateSequenceNumbers(true);
        diagram.setShowDiagramFrame(false);
        diagram.setShowActivations(true);
        String[] names = {"Customer","SearchUI","SpeechService","QueryService","SearchService","RankingService","ProductRepository"};
        String[] types = {"actor","boundary","control","control","control","control","entity"};
        IModelElement[] models = new IModelElement[names.length];
        IShapeUIModel[] views = new IShapeUIModel[names.length];
        int[] centers = new int[names.length];
        for(int i=0;i<names.length;i++) {
            IInteractionLifeLine lifeline = factory.createInteractionLifeLine();
            lifeline.setName(names[i]);
            if (i == 0) {
                lifeline.setBaseClassifier(customerActor);
            } else {
                IClass classifier = factory.createClass();
                classifier.setName(names[i]);
                classifier.addStereotype(types[i]);
                lifeline.setBaseClassifier(classifier);
            }
            models[i] = lifeline;
            views[i] = (IShapeUIModel) dm.createDiagramElement(diagram,models[i]);
            int x = 25+i*185;
            style(views[i],x,25,150,850,Color.WHITE);
            if (views[i] instanceof IInteractionLifeLineUIModel)
                ((IInteractionLifeLineUIModel) views[i]).setShowClassifier(false);
            if (i == 0) {
                if (views[i].getFillColor() != null)
                    views[i].getFillColor().setTransparency(100, true);
                if (views[i].getLineModel() != null)
                    views[i].getLineModel().setTransparency(100, true);
                views[i].getElementFont().setColor(Color.WHITE);
                IShapeUIModel actorView = (IShapeUIModel) dm.createDiagramElement(diagram,customerActor);
                style(actorView,x+52,25,46,58,Color.WHITE);
                actorView.getCaptionUIModel().setBounds(x+15,83,120,22);
            }
            centers[i]=x+75;
        }
        int[][] edges = {{0,1},{1,2},{2,1},{1,3},{3,1},{1,4},{4,6},{6,4},{4,5},{5,4},{4,1},{1,0}};
        String[] labels = {
            "provide voice query","transcribe(transcript)","transcript",
            "voice_query(text)","common query","search(query)",
            "all_products()","product candidates","rank(candidates, query)",
            "ranked products","top results + scores","display results"
        };
        for(int i=0;i<edges.length;i++) {
            int from=edges[i][0],to=edges[i][1];
            message(diagram,models[from],models[to],views[from],views[to],labels[i],
                    centers[from],centers[to],125+i*58,
                    i==2||i==4||i==7||i==9||i==10);
        }
        activation(diagram,(IInteractionLifeLine)models[1],centers[1],123,775);
        activation(diagram,(IInteractionLifeLine)models[2],centers[2],181,243);
        activation(diagram,(IInteractionLifeLine)models[3],centers[3],297,359);
        activation(diagram,(IInteractionLifeLine)models[4],centers[4],413,707);
        activation(diagram,(IInteractionLifeLine)models[5],centers[5],587,649);
        activation(diagram,(IInteractionLifeLine)models[6],centers[6],471,533);
        export(diagram,"03_sequence_voice");
    }

    @Override public void invoke(String[] args) {
        try {
            ProjectManager pm = ApplicationManager.instance().getProjectManager();
            // The CLI loads an empty seed project. Creating a fresh project in
            // headless mode raises a Swing dialog, so clear the seed's models.
            java.util.List<IModelElement> old = new ArrayList<>();
            java.util.Iterator<?> iterator = pm.getProject().modelElementIterator();
            while(iterator.hasNext()) old.add((IModelElement) iterator.next());
            for(IModelElement element : old) {
                try { element.delete(); } catch(UnsupportedOperationException ignored) { }
            }
            useCaseDiagram(); architectureClassDiagram(); sequenceDiagram();
            File target = new File(root,"Assignment06_V01_Multimodal_Search.vpp");
            if(!pm.saveProjectAs(target)) throw new IllegalStateException("Cannot save project");
            System.out.println("ASSIGNMENT06_BUILD_SUCCESS " + target.getAbsolutePath());
        } catch(Throwable error) { error.printStackTrace(); throw new RuntimeException(error); }
    }
}
